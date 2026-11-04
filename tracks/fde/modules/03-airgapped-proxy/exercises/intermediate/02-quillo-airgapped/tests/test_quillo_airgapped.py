import hashlib
import json
import shlex
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import fdekit
from testkit import ROOT, Exercise, run_sandboxed

ex = Exercise(__file__)
VERSION = "1.0.0"
BUNDLE = ROOT / "tracks" / "fde" / "product" / "dist" / f"quillo-{VERSION}.tar"
TOOLS = ROOT / "data" / "raw" / "fde-tools"
COMPOSE = TOOLS / "docker-compose-v5.6.1" / "docker-compose-linux-x86_64"
COMPOSE_SHA256 = "47737f4236e6d3ccea7291995203f8f018058783b4c3a9469119811a0b5db8c0"
PORT = 18080
MEMORY_MB = 5120
PACK_TIMEOUT = 120
INSTALL_TIMEOUT = 240
SERVICES = {"db", "llm", "embed", "api", "worker"}


def require_inputs() -> None:
    if not BUNDLE.is_file():
        pytest.skip("Chưa có bundle quillo. Dựng một lần (vài phút): nice -n 15 uv run python "
                    f"tracks/fde/product/release.py build --version {VERSION} --out tracks/fde/product/dist")
    if not COMPOSE.is_file():
        pytest.skip(f"Chưa có binary docker compose đã ghim ở {COMPOSE.relative_to(ROOT)}; tải theo phần "
                    "'0. Cài đặt' của README module 03")
    with COMPOSE.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != COMPOSE_SHA256:
            pytest.skip(f"{COMPOSE.relative_to(ROOT)} sai sha256; xoá rồi tải lại theo README module 03")


def flip_offset(bundle: Path) -> int:
    with tarfile.open(bundle) as tar:
        member = max(tar.getmembers(), key=lambda m: m.size)
        return member.offset_data + member.size // 2


def flip(m, offset: int) -> None:
    code = (f"f=open('/home/fde/usb/quillo-{VERSION}.tar','r+b'); f.seek({offset}); b=f.read(1); f.seek({offset}); "
            "f.write(bytes([b[0]^0xff])); f.close()")
    m.ssh(f"python3 -c \"{code}\"", timeout=30, check=True)


def forge_sums(m) -> None:
    code = ("import hashlib, re; t = 'quillo-" + VERSION + ".tar'; d = hashlib.sha256(); "
            "f = open('/home/fde/usb/' + t, 'rb'); [d.update(c) for c in iter(lambda: f.read(1 << 20), b'')]; "
            "p = '/home/fde/usb/SHA256SUMS'; s = open(p).read(); "
            "n = re.sub(r'^[0-9a-f]{64}( +\\*?)' + re.escape(t) + '$', lambda x: d.hexdigest() + x.group(1) + t, s, "
            "flags=re.M); assert n != s, 'SHA256SUMS không có dòng cho ' + t; open(p, 'w').write(n)")
    forged = sh(m, f"cp /home/fde/usb/SHA256SUMS /home/fde/SHA256SUMS.orig && python3 -c {shlex.quote(code)}", 60)
    assert forged.returncode == 0, f"Test không viết lại được SHA256SUMS trên USB:\n{forged.stderr[-800:]}"


def sh(m, cmd: str, timeout: float) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def untouched(m, site, case: str) -> None:
    assert not registry(site, "/v2/_catalog").get("repositories"), (
        f"{case}: install.sh vẫn đẩy image lên registry nội bộ")
    left = sh(m, "docker images -q; docker ps -aq", 30).stdout.strip()
    assert not left, f"{case}: install.sh vẫn nạp image hoặc tạo container"


def install(m) -> subprocess.CompletedProcess:
    try:
        return m.ssh("cd /tmp && sudo -n bash /home/fde/usb/install.sh", timeout=INSTALL_TIMEOUT)
    except subprocess.TimeoutExpired:
        pytest.fail(f"install.sh chạy quá {INSTALL_TIMEOUT} s trong VM")


def registry(site, path: str) -> dict:
    with urllib.request.urlopen(f"http://{site.registry_host}{path}", timeout=10) as response:
        return json.load(response)


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


def test_install_quillo_from_usb_on_lawfirm_staging():
    require_inputs()
    timings = {}
    with tempfile.TemporaryDirectory(dir="/var/tmp", prefix="fde-usb-", ignore_cleanup_errors=True) as tmp:
        work = Path(tmp)
        usb = work / "usb"
        started = time.monotonic()
        try:
            packed = run_sandboxed(["sh", ex.path("pack_usb.sh"), BUNDLE, TOOLS, usb], writable=[work], cwd=work,
                                   env={}, timeout=PACK_TIMEOUT)
        except subprocess.TimeoutExpired:
            pytest.fail(f"pack_usb.sh chạy quá {PACK_TIMEOUT} s")
        assert packed.returncode == 0, f"pack_usb.sh thoát mã {packed.returncode}\nstderr:\n{packed.stderr[-2000:]}"
        for name in (f"quillo-{VERSION}.tar", "install.sh", "SHA256SUMS"):
            assert (usb / name).is_file(), f"USB phải có {name} ở thư mục gốc"
        offset = flip_offset(usb / f"quillo-{VERSION}.tar")
        timings["pack"] = time.monotonic() - started

        with fdekit.customer_site("lawfirm-staging", memory_mb=MEMORY_MB, forwards=(PORT,)) as s:
            m = s.vm
            timings["boot"] = time.monotonic() - started - timings["pack"]
            mark = time.monotonic()
            m.put(usb, "/home/fde/usb")
            timings["usb"] = time.monotonic() - mark

            flip(m, offset)
            mark = time.monotonic()
            broken = install(m)
            timings["tampered"] = time.monotonic() - mark
            assert broken.returncode != 0, "Bundle trên USB bị hỏng một byte mà install.sh vẫn thoát 0"
            untouched(m, s, "Bundle hỏng (SHA256SUMS không khớp)")

            forge_sums(m)
            mark = time.monotonic()
            forged = install(m)
            timings["forged"] = time.monotonic() - mark
            assert forged.returncode != 0, (
                "Một tệp trong bundle bị sửa và SHA256SUMS được viết lại cho khớp, mà install.sh vẫn thoát 0: "
                "manifest.json bên trong bundle chưa được kiểm")
            untouched(m, s, "Bundle bị sửa (SHA256SUMS khớp, manifest không khớp)")
            flip(m, offset)
            restored = sh(m, "cp /home/fde/SHA256SUMS.orig /home/fde/usb/SHA256SUMS", 30)
            assert restored.returncode == 0

            mark = time.monotonic()
            done = install(m)
            timings["install"] = time.monotonic() - mark
            assert done.returncode == 0, (
                f"install.sh thoát mã {done.returncode}\nstdout:\n{done.stdout[-2500:]}\nstderr:\n{done.stderr[-2500:]}")
            body = healthz(f"http://127.0.0.1:{m.port(PORT)}/healthz")
            assert body.get("version") == VERSION, f"/healthz trả {body}, cần version {VERSION}"

            ps = m.ssh("docker ps --filter label=com.docker.compose.project=quillo "
                       "--format '{{.Label \"com.docker.compose.service\"}} {{.Image}}'", timeout=30).stdout
            running = dict(line.split(" ", 1) for line in ps.strip().splitlines())
            assert SERVICES <= set(running), f"Project compose 'quillo' thiếu dịch vụ: {sorted(SERVICES - set(running))}"
            for service, image in sorted(running.items()):
                assert image.startswith(f"{s.registry}/"), (
                    f"Dịch vụ {service} chạy image {image}, phải lấy từ registry nội bộ {s.registry}")
                repo, _, tag = image[len(s.registry) + 1:].rpartition(":")
                tags = registry(s, f"/v2/{repo}/tags/list").get("tags") or []
                assert tag in tags, f"Registry nội bộ không có {repo}:{tag} mà {service} đang chạy"
    timings["total"] = time.monotonic() - started
    print("thời gian (s): " + ", ".join(f"{k} {v:.1f}" for k, v in timings.items()))
