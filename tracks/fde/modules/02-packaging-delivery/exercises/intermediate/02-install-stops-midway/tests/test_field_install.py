import json
import subprocess
import time
import urllib.error
import urllib.request

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
KIT = ex.dir / "beacon"
KIT_FILES = ("beacon.py", "beacon.service", "beacon.env", "make_bundle.py")
PORT = 8088
RUN_TIMEOUT = 200
RELEASE_MIB = 2400


def put_kit(m) -> None:
    m.ssh("mkdir -p /home/fde/kit", check=True)
    for name in KIT_FILES:
        m.put(KIT / name, f"/home/fde/kit/{name}")
    m.put(ex.path("install.sh"), "/home/fde/install.sh")


def bundle(m, version: str, mib: int) -> dict:
    out = m.ssh(f"python3 /home/fde/kit/make_bundle.py {version} {mib} /home/fde/beacon-{version}.tar", timeout=180)
    assert out.returncode == 0, f"Không dựng được bundle {version} trong VM: {out.stderr}"
    return json.loads(out.stdout)


def install(m, version: str) -> subprocess.CompletedProcess:
    try:
        return m.ssh(f"sudo -n bash /home/fde/install.sh /home/fde/beacon-{version}.tar", timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        pytest.fail(f"install.sh với bundle {version} chạy quá {RUN_TIMEOUT} s mà chưa xong (treo?)")


def serving(m, version: str, weights_sha256: str, timeout: float = 120) -> None:
    url = f"http://127.0.0.1:{m.port(PORT)}/healthz"
    deadline = time.monotonic() + timeout
    last = "chưa có phản hồi"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                body = json.load(response)
            if body.get("version") == version and body.get("weights_sha256") == weights_sha256:
                return
            last = json.dumps(body)
        except urllib.error.HTTPError as error:
            last = f"HTTP {error.code}"
        except OSError as error:
            last = str(error)
        time.sleep(1)
    pytest.fail(f"Sau {timeout:.0f} s beacon chưa phục vụ bản {version} với đúng model ({url}: {last})")


def ok(result: subprocess.CompletedProcess, version: str) -> None:
    assert result.returncode == 0, (
        f"install.sh {version} thoát mã {result.returncode}\nstdout:\n{result.stdout[-1500:]}\n"
        f"stderr:\n{result.stderr[-1500:]}")


@pytest.mark.parametrize("profile", ["lab-open", "hospital"])
def test_upgrade_with_new_model(profile):
    with fdekit.vm(profile, memory_mb=1024, forwards=(PORT,)) as m:
        put_kit(m)
        first = bundle(m, "1.0.0", 4)
        bundle(m, "1.2.0", 4)
        assert m.ssh("truncate -s 2M /home/fde/beacon-1.2.0.tar", timeout=30).returncode == 0

        ok(install(m, "1.0.0"), "1.0.0")
        serving(m, "1.0.0", first["files"]["models/weights.bin"]["sha256"])

        upgrade = bundle(m, "1.1.0", RELEASE_MIB)
        ok(install(m, "1.1.0"), "1.1.0")
        serving(m, "1.1.0", upgrade["files"]["models/weights.bin"]["sha256"])

        broken = install(m, "1.2.0")
        assert broken.returncode != 0, "Bundle 1.2.0 bị chép thiếu (tar cụt) mà install.sh vẫn thoát 0"
        serving(m, "1.1.0", upgrade["files"]["models/weights.bin"]["sha256"], timeout=30)
        assert m.ssh("systemctl is-enabled beacon", timeout=30).stdout.strip() == "enabled"
