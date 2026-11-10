import hashlib
import io
import json
import secrets
import shlex
import subprocess
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import fdekit
from testkit import ROOT, Exercise

ex = Exercise(__file__)
TOOLS = ROOT / "data" / "raw" / "fde-tools"
COMPOSE = TOOLS / "docker-compose-v5.6.1" / "docker-compose-linux-x86_64"
COMPOSE_SHA256 = "47737f4236e6d3ccea7291995203f8f018058783b4c3a9469119811a0b5db8c0"
BUSYBOX = TOOLS / "busybox-1.35.0" / "busybox"
BUSYBOX_SHA256 = "6e123e7f3202a8c1e9b1f94d8941580a25135382b99e8d3e34fb858bba311348"
BUSYBOX_URL = "https://busybox.net/downloads/binaries/1.35.0-x86_64-linux-musl/busybox"
BUNDLE = "/home/fde/notice-bundle"
IMAGE_TAG = "localhost/notice:1.0"
PORT = 18081
DEPLOY_TIMEOUT = 120
SERVE_WAIT = 30
LOGOUT_SECONDS = 10
START = b"""#!/bin/sh
set -e
/bin/busybox mkdir -p /tmp/www
/bin/busybox cat /etc/notice/notice.conf > /tmp/www/index.html
exec /bin/busybox httpd -f -v -p 8080 -h /tmp/www
"""


def require_tools() -> None:
    for path, sha, how in (
        (COMPOSE, COMPOSE_SHA256, "tải theo phần '0. Cài đặt' của README module 03"),
        (BUSYBOX, BUSYBOX_SHA256, f"mkdir -p {BUSYBOX.parent.relative_to(ROOT)} && curl -fLo "
                                  f"{BUSYBOX.relative_to(ROOT)} {BUSYBOX_URL} && echo '{BUSYBOX_SHA256}  "
                                  f"{BUSYBOX.relative_to(ROOT)}' | sha256sum -c -"),
    ):
        if not path.is_file():
            pytest.skip(f"Chưa có {path.relative_to(ROOT)}; {how}")
        with path.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != sha:
                pytest.skip(f"{path.relative_to(ROOT)} sai sha256; xoá rồi tải lại ({how})")


def _entry(name: str, *, data: bytes | None = None, mode: int = 0o755, kind: bytes = tarfile.REGTYPE,
           link: str = "") -> tuple[tarfile.TarInfo, io.BytesIO | None]:
    info = tarfile.TarInfo(name)
    info.mode, info.type, info.linkname, info.mtime = mode, kind, link, 0
    if data is not None:
        info.size = len(data)
    return info, (io.BytesIO(data) if data is not None else None)


def build_image(out: Path) -> None:
    """Image docker-archive `localhost/notice:1.0` (busybox tĩnh + /app/start), dựng tất định, không cần Docker."""
    layer = io.BytesIO()
    with tarfile.open(fileobj=layer, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for info, data in (_entry("bin", kind=tarfile.DIRTYPE), _entry("bin/busybox", data=BUSYBOX.read_bytes()),
                           _entry("bin/sh", kind=tarfile.SYMTYPE, link="busybox", mode=0o777),
                           _entry("app", kind=tarfile.DIRTYPE), _entry("app/start", data=START),
                           _entry("tmp", kind=tarfile.DIRTYPE, mode=0o1777), _entry("etc", kind=tarfile.DIRTYPE)):
            tar.addfile(info, data)
    blob = layer.getvalue()
    diff = hashlib.sha256(blob).hexdigest()
    config = json.dumps({
        "architecture": "amd64", "os": "linux", "created": "2026-01-01T00:00:00Z",
        "config": {"Entrypoint": ["/app/start"], "ExposedPorts": {"8080/tcp": {}}, "WorkingDir": "/"},
        "rootfs": {"type": "layers", "diff_ids": [f"sha256:{diff}"]},
        "history": [{"created": "2026-01-01T00:00:00Z", "created_by": "fde module 04"}],
    }, sort_keys=True).encode()
    name = hashlib.sha256(config).hexdigest()
    manifest = json.dumps([{"Config": f"{name}.json", "RepoTags": [IMAGE_TAG], "Layers": [f"{diff}/layer.tar"]}])
    with tarfile.open(out, "w", format=tarfile.USTAR_FORMAT) as tar:
        for path, data in ((f"{diff}/layer.tar", blob), (f"{name}.json", config), ("manifest.json", manifest.encode())):
            info, handle = _entry(path, data=data, mode=0o644)
            tar.addfile(info, handle)


def sh(m, cmd: str, timeout: float = 30) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def write_notice(m, message: str) -> None:
    done = sh(m, f"printf '%s\\n' {shlex.quote(message)} > {BUNDLE}/config/notice.conf")
    assert done.returncode == 0, f"Test không ghi được {BUNDLE}/config/notice.conf: {done.stderr}"


def deploy(m, attempt: str) -> None:
    run = sh(m, f"cd /tmp && sh {BUNDLE}/deploy.sh", timeout=DEPLOY_TIMEOUT)
    assert run.returncode == 0, (
        f"deploy.sh ({attempt}) thoát mã {run.returncode}\nstdout:\n{run.stdout[-2000:]}\nstderr:\n{run.stderr[-2500:]}")


def fetch(url: str) -> tuple[int | None, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, ""
    except OSError as error:
        return None, str(error)


def wait_message(m, message: str, attempt: str) -> None:
    url = f"http://127.0.0.1:{m.port(PORT)}/"
    deadline = time.monotonic() + SERVE_WAIT
    status, body = None, ""
    while time.monotonic() < deadline:
        status, body = fetch(url)
        if status == 200 and body.strip() == message:
            return
        time.sleep(2)
    logs = sh(m, "podman ps -a --format '{{.Names}} {{.Status}}'; for c in $(podman ps -aq); do podman logs --tail 5 $c; done")
    pytest.fail(f"{attempt}: cổng {PORT} của VM không trả đúng nội dung notice.conf sau {SERVE_WAIT} s "
                f"(HTTP {status}, nhận {body.strip()[:120]!r}, cần {message!r})\npodman:\n{logs.stdout[-1500:]}"
                f"{logs.stderr[-500:]}")


def inspect_service(m) -> dict:
    ids = sh(m, "podman ps -q --filter label=com.docker.compose.project=notice "
                "--filter label=com.docker.compose.service=notice").stdout.split()
    assert len(ids) == 1, f"Cần đúng một container đang chạy của dịch vụ notice trong project compose 'notice', có {len(ids)}"
    raw = sh(m, f"podman inspect {ids[0]}").stdout
    return json.loads(raw)[0]


def check_container(m) -> None:
    info = inspect_service(m)
    label = info.get("ProcessLabel") or ""
    assert ":container_t:" in label, (
        f"Container phải chạy dưới SELinux type container_t (đang {label!r}); không tắt SELinux cho container")
    assert not info.get("HostConfig", {}).get("Privileged"), "Container không được chạy privileged"
    mounts = [mt for mt in info.get("Mounts", []) if mt.get("Destination") == "/etc/notice"]
    assert mounts and mounts[0].get("Source") == f"{BUNDLE}/config", (
        f"/etc/notice trong container phải là bind mount của {BUNDLE}/config (đang {mounts})")
    mode = sh(m, "getenforce").stdout.strip()
    assert mode == "Enforcing", f"SELinux phải vẫn Enforcing, đang {mode!r}"


def test_compose_on_rootless_podman_lawfirm_hardened(tmp_path):
    require_tools()
    build_image(tmp_path / "notice-image.tar")
    first, second = f"lich-truc-{secrets.token_hex(5)}", f"lich-truc-{secrets.token_hex(5)}"
    with fdekit.customer_site("lawfirm-hardened", memory_mb=2048, forwards=(PORT,)) as s:
        m = s.vm
        assert sh(m, f"mkdir -p {BUNDLE}/config").returncode == 0
        m.put(tmp_path / "notice-image.tar", f"{BUNDLE}/notice-image.tar")
        m.put(COMPOSE, f"{BUNDLE}/docker-compose")
        m.put(ex.path("compose.yaml"), f"{BUNDLE}/compose.yaml")
        m.put(ex.path("deploy.sh"), f"{BUNDLE}/deploy.sh")
        assert sh(m, f"chmod 0755 {BUNDLE}/docker-compose").returncode == 0

        write_notice(m, first)
        deploy(m, "lần 1")
        wait_message(m, first, "lần 1")
        check_container(m)

        write_notice(m, second)
        time.sleep(LOGOUT_SECONDS)
        status, body = fetch(f"http://127.0.0.1:{m.port(PORT)}/")
        assert status == 200 and body.strip() == first, (
            f"Không còn phiên SSH nào {LOGOUT_SECONDS} s thì dịch vụ phải vẫn phục vụ (HTTP {status}, {body.strip()[:80]!r})")
        deploy(m, "lần 2, phiên SSH mới, notice.conf đã đổi")
        wait_message(m, second, "lần 2")
        check_container(m)
