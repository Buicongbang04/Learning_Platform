import json
import shlex
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
RUN_TIMEOUT = 180
STATE = ("sudo -n find /opt/beacon /etc/beacon /etc/systemd/system/beacon.service "
         "\\( -type d -printf '%p %i d\\n' \\) -o -printf '%p %i %y %l %s %T@\\n' 2>/dev/null | sort; "
         "systemctl show beacon -p MainPID -p ActiveEnterTimestamp -p UnitFileState")


def put_kit(m) -> None:
    m.ssh("mkdir -p /home/fde/kit", check=True)
    for name in KIT_FILES:
        m.put(KIT / name, f"/home/fde/kit/{name}")
    m.put(ex.path("install.sh"), "/home/fde/install.sh")


def bundle(m, version: str, *flags: str) -> dict:
    out = m.ssh(f"python3 /home/fde/kit/make_bundle.py {version} 4 /home/fde/beacon-{version}.tar {' '.join(flags)}",
                timeout=120)
    assert out.returncode == 0, f"Không dựng được bundle {version} trong VM: {out.stderr}"
    return json.loads(out.stdout)


def install(m, version: str) -> subprocess.CompletedProcess:
    try:
        return m.ssh(f"sudo -n bash /home/fde/install.sh /home/fde/beacon-{version}.tar", timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        pytest.fail(f"install.sh với bundle {version} chạy quá {RUN_TIMEOUT} s mà chưa xong (treo?)")


def healthz(m, timeout: float = 60) -> dict:
    url = f"http://127.0.0.1:{m.port(PORT)}/healthz"
    deadline = time.monotonic() + timeout
    last = "chưa có phản hồi"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            last = f"HTTP {error.code}"
        except OSError as error:
            last = str(error)
        time.sleep(1)
    pytest.fail(f"beacon không trả lời {url} sau {timeout:.0f} s ({last})")


def serving(m, version: str, greeting: str, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    body = {}
    while time.monotonic() < deadline:
        body = healthz(m, timeout=max(1.0, deadline - time.monotonic()))
        if body.get("version") == version and body.get("status") == "ok":
            break
        time.sleep(1)
    assert body.get("version") == version, f"Dịch vụ đang chạy bản {body.get('version')!r}, cần {version!r}"
    assert body.get("greeting") == greeting, (
        f"BEACON_GREETING đang là {body.get('greeting')!r}, cần {greeting!r} (cấu hình của khách phải được giữ)")


def state(m) -> str:
    return m.ssh(STATE, timeout=30).stdout


def last_log(m) -> list[str]:
    out = m.ssh("sudo -n tail -n 1 /var/log/beacon/install.log", timeout=30).stdout.split()
    return out[-2:]


def check_run(m, result: subprocess.CompletedProcess, version: str, outcome: str, ok: bool) -> None:
    detail = f"\nstdout:\n{result.stdout[-1500:]}\nstderr:\n{result.stderr[-1500:]}"
    if ok:
        assert result.returncode == 0, f"install.sh {version} thoát mã {result.returncode}, cần 0{detail}"
    else:
        assert result.returncode != 0, f"install.sh {version} thoát 0, cần mã khác 0 ({outcome}){detail}"
    assert last_log(m) == [version, outcome], (
        f"Dòng cuối /var/log/beacon/install.log phải kết thúc bằng '{version} {outcome}', đang là {last_log(m)}")


def test_install_rerun_upgrade_and_rollback():
    with fdekit.vm("lab-open", memory_mb=1024, forwards=(PORT,)) as m:
        put_kit(m)
        for version in ("1.0.0", "1.1.0"):
            bundle(m, version)
        bundle(m, "1.2.0", "--bad-sha")
        bundle(m, "1.3.0", "--broken-app")

        check_run(m, install(m, "1.0.0"), "1.0.0", "installed", ok=True)
        serving(m, "1.0.0", "xin chao")
        assert m.ssh("systemctl is-enabled beacon", timeout=30).stdout.strip() == "enabled", (
            "beacon phải được enable để tự chạy lại sau khi máy khởi động lại")

        before = state(m)
        check_run(m, install(m, "1.0.0"), "1.0.0", "unchanged", ok=True)
        assert state(m) == before, "Chạy lại cùng bundle phải không đổi gì (tệp, symlink, tiến trình dịch vụ)"

        edit = ("sudo -n sed -i 's/^BEACON_GREETING=.*/BEACON_GREETING=chao khoa noi/' /etc/beacon/beacon.env && "
                "sudo -n systemctl restart beacon")
        assert m.ssh(edit, timeout=60).returncode == 0
        serving(m, "1.0.0", "chao khoa noi")
        before = state(m)
        check_run(m, install(m, "1.0.0"), "1.0.0", "unchanged", ok=True)
        assert state(m) == before, "Sau khi khách sửa cấu hình, chạy lại cùng bundle vẫn phải không đổi gì"

        check_run(m, install(m, "1.1.0"), "1.1.0", "installed", ok=True)
        serving(m, "1.1.0", "chao khoa noi")
        before = state(m)
        check_run(m, install(m, "1.1.0"), "1.1.0", "unchanged", ok=True)
        assert state(m) == before, "Chạy lại bundle 1.1.0 phải không đổi gì"

        check_run(m, install(m, "1.2.0"), "1.2.0", "failed", ok=False)
        assert state(m) == before, "Bundle sai sha256 phải bị từ chối trước khi đụng vào bản đang chạy, không để lại rác"
        serving(m, "1.1.0", "chao khoa noi")

        check_run(m, install(m, "1.3.0"), "1.3.0", "rolled-back", ok=False)
        serving(m, "1.1.0", "chao khoa noi")
        assert m.ssh("systemctl is-active beacon", timeout=30).stdout.strip() == "active"
