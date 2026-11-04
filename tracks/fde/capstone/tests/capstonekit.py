"""Hàm dùng chung cho bộ chấm capstone FDE (không phải test)."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import pytest
import yaml

from testkit import ROOT, run_sandboxed

VERSION = "1.0.0"
RELEASE_NAME = f"quillo-{VERSION}.tar"
RELEASE_DIR = ROOT / "tracks" / "fde" / "product" / "dist"
RELEASE_TAR = RELEASE_DIR / RELEASE_NAME
COMPOSE_BIN = ROOT / "data" / "raw" / "fde-tools" / "docker-compose-v5.6.1" / "docker-compose-linux-x86_64"
COMPOSE_SHA256 = "47737f4236e6d3ccea7291995203f8f018058783b4c3a9469119811a0b5db8c0"
REQUIREMENTS = ROOT / "tracks" / "fde" / "product" / "REQUIREMENTS.yaml"
PORT = 18080
MEMORY_MB = 5120
REMOTE_BUNDLE = "/home/fde/bundle"
SERVICES = {"db", "llm", "embed", "api", "worker"}
BUNDLE_TIMEOUT = 120
INSTALL_TIMEOUT = 250
VERIFY_TIMEOUT = 60
FRONTMATTER = re.compile(r"^---\n([\s\S]*?)\n---\n")
BUILD_RELEASE = (f"nice -n 15 uv run python tracks/fde/product/release.py build --version {VERSION} "
                 "--out tracks/fde/product/dist")


def need_files(repo: Path, *rels: str) -> None:
    missing = [rel for rel in rels if not (repo / rel).is_file()]
    if missing:
        pytest.fail(f"Repo {repo} còn thiếu: {', '.join(missing)} (xem đề milestone)")


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


@dataclass(frozen=True)
class Release:
    tar: Path
    sha256: str


@cache
def release() -> Release:
    """Bản phát hành quillo 1.0.0 và binary compose đã ghim; thiếu thì skip kèm lệnh."""
    if not RELEASE_TAR.is_file():
        pytest.skip(f"Chưa có bundle quillo. Dựng một lần (vài phút): {BUILD_RELEASE}")
    if not COMPOSE_BIN.is_file() or sha256(COMPOSE_BIN) != COMPOSE_SHA256:
        pytest.skip(f"Chưa có (hoặc sai sha256) binary compose đã ghim ở {COMPOSE_BIN.relative_to(ROOT)}; tải theo "
                    "phần '0. Cài đặt' của README module 03-airgapped-proxy")
    return Release(RELEASE_TAR, sha256(RELEASE_TAR))


def release_member(rel: str) -> bytes:
    with tarfile.open(release().tar) as tar:
        handle = tar.extractfile(f"quillo-{VERSION}/{rel}")
        assert handle is not None
        return handle.read()


def big_tmp() -> tempfile.TemporaryDirectory:
    """Thư mục tạm trên đĩa (không phải tmpfs /tmp): bundle ~1,1 GB."""
    return tempfile.TemporaryDirectory(dir="/var/tmp", prefix="fde-capstone-", ignore_cleanup_errors=True)


def output(result: subprocess.CompletedProcess, limit: int = 2500) -> str:
    return f"stdout:\n{result.stdout[-limit:]}\nstderr:\n{result.stderr[-limit:]}"


def make(repo: Path, *args: str, writable: list[Path] | tuple = (), timeout: float = 60) -> subprocess.CompletedProcess:
    """`make -C <repo> args...` trong sandbox: repo chỉ đọc, chỉ ghi được `writable`."""
    cmd = ["make", "--no-print-directory", "-C", str(repo), *args]
    try:
        return run_sandboxed(cmd, writable=list(writable), cwd=repo, env={}, timeout=timeout, input="")
    except subprocess.TimeoutExpired:
        targets = " ".join(a for a in args if "=" not in a)
        pytest.fail(f"`make {targets}` chạy quá {timeout:.0f} s")


def bundle_vars(site: str, dest: Path, sha: str | None = None) -> list[str]:
    return [f"SITE={site}", f"BUNDLE_DIR={dest}", f"QUILLO_RELEASE_DIR={RELEASE_DIR}",
            f"QUILLO_RELEASE_SHA256={sha or release().sha256}", f"COMPOSE_BIN={COMPOSE_BIN}"]


def build_bundle(repo: Path, site: str, dest: Path) -> subprocess.CompletedProcess:
    result = make(repo, "bundle", *bundle_vars(site, dest), writable=[dest.parent], timeout=BUNDLE_TIMEOUT)
    assert result.returncode == 0, f"make bundle SITE={site} thoát mã {result.returncode}\n{output(result)}"
    assert (dest / "SHA256SUMS").is_file(), f"make bundle không tạo {dest}/SHA256SUMS"
    return result


def ssh_vars(m) -> list[str]:
    return [f"SSH={shlex.join(m.ssh_command())}", f"REMOTE_BUNDLE={REMOTE_BUNDLE}"]


def make_on(repo: Path, m, target: str, timeout: float) -> subprocess.CompletedProcess:
    return make(repo, target, *ssh_vars(m), timeout=timeout)


def vm_sh(m, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def healthz(url: str, timeout: float = 60) -> dict:
    deadline = time.monotonic() + timeout
    last = "chưa có phản hồi"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return json.load(response)
        except urllib.error.HTTPError as error:
            last = f"HTTP {error.code}"
        except OSError as error:
            last = str(error)
        time.sleep(2)
    pytest.fail(f"{url} không trả 200 sau {timeout:.0f} s ({last})")


def quillo_containers(m) -> dict[str, dict]:
    """Container của project compose `quillo` trong VM: dịch vụ → id, image, trạng thái, StartedAt."""
    ids = vm_sh(m, "docker ps -aq --filter label=com.docker.compose.project=quillo", 30).stdout.split()
    if not ids:
        return {}
    fmt = ('{{index .Config.Labels "com.docker.compose.service"}}|{{.Id}}|{{.Config.Image}}|{{.State.Status}}|'
           '{{.State.StartedAt}}')
    raw = vm_sh(m, f"docker inspect -f {shlex.quote(fmt)} {' '.join(ids)}", 30).stdout
    found = {}
    for line in raw.strip().splitlines():
        service, cid, image, status, started = line.split("|")
        found[service] = {"id": cid, "image": image, "status": status, "started": started}
    return found


def frontmatter(path: Path) -> dict:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8").replace("\r\n", "\n"))
    if not match:
        pytest.fail(f"{path.name} phải mở đầu bằng frontmatter YAML giữa hai dòng '---'")
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        pytest.fail(f"Frontmatter của {path.name} không phải YAML hợp lệ: {error}")
    if not isinstance(data, dict):
        pytest.fail(f"Frontmatter của {path.name} phải là một mapping YAML")
    return data


def read_sums(path: Path) -> dict[str, str]:
    sums = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64}) [ *](.+)", line)
        assert match, f"SHA256SUMS dòng {n} không đúng định dạng sha256sum: {line!r}"
        sums[match.group(2).removeprefix("./")] = match.group(1)
    return sums
