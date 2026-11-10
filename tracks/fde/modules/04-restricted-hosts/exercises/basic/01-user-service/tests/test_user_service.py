import secrets
import shlex
import subprocess
import time

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
BUNDLE = "/home/fde/heartbeat-bundle"
CONF = "/home/fde/.config/heartbeat/heartbeat.env"
LOG = "/home/fde/.local/state/heartbeat/beats.log"
UNIT = "heartbeat.service"
INSTALL_TIMEOUT = 60
LOGOUT_SECONDS = 25
MAX_GAP = 6


def sh(m, cmd: str, timeout: float = 30) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def write_conf(m, token: str) -> None:
    body = shlex.quote(f"TOKEN={token}\nINTERVAL=1\n")
    done = sh(m, f"mkdir -p ~/.config/heartbeat && printf %s {body} > {CONF}")
    assert done.returncode == 0, f"Test không ghi được {CONF}: {done.stderr}"


def install(m, attempt: str) -> None:
    run = sh(m, f"cd /tmp && sh {BUNDLE}/install.sh", timeout=INSTALL_TIMEOUT)
    assert run.returncode == 0, (
        f"install.sh ({attempt}) thoát mã {run.returncode}\nstdout:\n{run.stdout[-1500:]}\nstderr:\n{run.stderr[-1500:]}")


def main_pid(m) -> int:
    out = sh(m, f"systemctl --user show -p MainPID --value {UNIT}").stdout.strip()
    return int(out or 0)


def beats(m) -> list[tuple[int, int, str]]:
    out = sh(m, f"cat {LOG} 2>/dev/null").stdout
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            rows.append((int(parts[0]), int(parts[1]), parts[2]))
    return rows


def wait_beat(m, token: str, pid: int, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(row[1] == pid and row[2] == token for row in beats(m)):
            return
        time.sleep(1)
    pytest.fail(f"Sau {timeout:.0f} s, {LOG} chưa có dòng nào của pid {pid} với token {token} trong cấu hình")


def vm_now(m) -> int:
    return int(sh(m, "date +%s").stdout.strip())


def active(m) -> str:
    return sh(m, f"systemctl --user is-active {UNIT}").stdout.strip()


def test_heartbeat_survives_restart_and_logout_on_bank():
    first, second = secrets.token_hex(6), secrets.token_hex(6)
    with fdekit.vm("bank", memory_mb=1024) as m:
        assert sh(m, f"mkdir -p {BUNDLE}").returncode == 0
        m.put(ex.dir / "heartbeat" / "heartbeat.sh", f"{BUNDLE}/heartbeat.sh")
        m.put(ex.path("install.sh"), f"{BUNDLE}/install.sh")
        m.put(ex.path("heartbeat.service"), f"{BUNDLE}/heartbeat.service")
        write_conf(m, first)
        install(m, "lần 1")
        install(m, "lần 2")

        assert active(m) == "active", f"{UNIT} của user fde chưa active sau khi cài: {active(m)!r}"
        enabled = sh(m, f"systemctl --user is-enabled {UNIT}").stdout.strip()
        assert enabled == "enabled", f"{UNIT} phải enabled để tự chạy khi user manager khởi động, đang là {enabled!r}"
        pid = main_pid(m)
        assert pid > 0, f"{UNIT} không có MainPID"
        wait_beat(m, first, pid)

        write_conf(m, second)
        restarted = sh(m, f"systemctl --user restart {UNIT}")
        assert restarted.returncode == 0, f"systemctl --user restart {UNIT} lỗi:\n{restarted.stderr}"
        new_pid = main_pid(m)
        assert new_pid > 0 and new_pid != pid, "Sau restart, MainPID phải là tiến trình mới"
        wait_beat(m, second, new_pid)

        left = vm_now(m)
        time.sleep(LOGOUT_SECONDS)
        back = vm_now(m)
        state = active(m)
        assert state == "active", (
            f"Không còn phiên SSH nào trong {LOGOUT_SECONDS} s; khi đăng nhập lại {UNIT} đang {state!r}")
        assert main_pid(m) == new_pid, (
            f"{UNIT} chạy lại với pid mới sau khi mọi phiên SSH đóng: dịch vụ đã chết khi bạn đăng xuất")
        stamps = [row[0] for row in beats(m) if row[1] == new_pid and left <= row[0] <= back]
        assert stamps, f"Trong lúc không ai đăng nhập ({LOGOUT_SECONDS} s), {UNIT} không ghi dòng nào"
        edges = [left] + stamps + [back]
        gap = max(b - a for a, b in zip(edges, edges[1:]))
        assert gap <= MAX_GAP, (
            f"Trong lúc không ai đăng nhập, {UNIT} ngừng ghi {gap} s (cho phép ≤{MAX_GAP} s với INTERVAL=1)")
