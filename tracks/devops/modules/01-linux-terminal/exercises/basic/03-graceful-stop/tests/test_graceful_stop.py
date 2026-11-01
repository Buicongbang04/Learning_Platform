import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None or not Path("/proc").is_dir(), reason="Cần bash và Linux (/proc)")

GRACEFUL = """
import signal, sys, time
def bye(*_):
    time.sleep({delay})
    open(sys.argv[1], "w").write("cleaned")
    sys.exit(0)
signal.signal(signal.SIGTERM, bye)
open(sys.argv[2], "w").write("ready")
while True:
    time.sleep(0.05)
"""
STUBBORN = """
import signal, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
open(sys.argv[2], "w").write("ready")
while True:
    time.sleep(0.05)
"""


def alive(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (FileNotFoundError, IndexError):
        return False
    return state != "Z"


def wait_ready(flag: Path) -> None:
    deadline = time.monotonic() + 10
    while not flag.exists():
        assert time.monotonic() < deadline, "Tiến trình thử không khởi động được"
        time.sleep(0.02)


def spawn_orphan(code: str, tmp_path: Path) -> tuple[int, Path]:
    """Chạy Python nền qua một shell trung gian để tiến trình mồ côi được init/subreaper thu dọn."""
    marker, ready = tmp_path / "cleaned", tmp_path / "ready"
    launcher = subprocess.run(
        [BASH, "-c", '"$1" -c "$2" "$3" "$4" </dev/null >/dev/null 2>&1 & echo $!', "_", sys.executable, code, str(marker), str(ready)],
        capture_output=True,
        text=True,
        timeout=10,
        start_new_session=True,
    )
    pid = int(launcher.stdout.strip())
    wait_ready(ready)
    return pid, marker


@pytest.fixture
def orphans():
    pids = []
    yield pids
    for pid in pids:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass


def run(tmp: Path, *args, script: Path | None = None):
    """Không dùng sandbox vì script phải gửi signal tới PID thật; bù lại chạy trong session riêng với env dựng từ đầu."""
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(tmp), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    start = time.monotonic()
    result = subprocess.run(
        [BASH, str(script or ex.path("graceful_stop.sh")), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=tmp,
        env=env,
        start_new_session=True,
    )
    return result, time.monotonic() - start


@pytest.mark.parametrize("args", [(), ("abc",), ("1",), ("0",), ("123", "x"), ("123", "-1")])
def test_bad_arguments(tmp_path, args):
    result, _ = run(tmp_path, *args)
    assert result.returncode == 2
    assert result.stderr.startswith("Usage:")


def test_missing_process(tmp_path):
    pid = 4194300
    while Path(f"/proc/{pid}").exists():
        pid -= 1
    result, _ = run(tmp_path, pid, 1)
    assert result.returncode == 1
    assert result.stderr.strip()
    assert result.stdout == ""


def test_graceful_process_gets_time_to_clean_up(tmp_path, orphans):
    pid, marker = spawn_orphan(GRACEFUL.format(delay=1.0), tmp_path)
    orphans.append(pid)
    result, elapsed = run(tmp_path, pid, 5)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"stopped {pid} SIGTERM"
    assert marker.read_text() == "cleaned", "Tiến trình phải được dọn dẹp xong (không bị KILL sớm)"
    assert not alive(pid)
    assert elapsed < 4, "Tiến trình đã dừng sau khoảng 1 giây, script không được chờ hết timeout"


def test_stubborn_process_is_killed_after_timeout(tmp_path, orphans):
    pid, marker = spawn_orphan(STUBBORN, tmp_path)
    orphans.append(pid)
    result, elapsed = run(tmp_path, pid, 1)
    assert result.returncode == 3, result.stderr
    assert result.stdout.strip() == f"killed {pid} SIGKILL"
    assert not alive(pid)
    assert elapsed >= 1, "Phải chờ hết timeout rồi mới SIGKILL"
    assert elapsed < 8


def test_default_timeout_is_ten_seconds(tmp_path, orphans):
    pid, _ = spawn_orphan(GRACEFUL.format(delay=0.2), tmp_path)
    orphans.append(pid)
    result, _ = run(tmp_path, pid)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"stopped {pid} SIGTERM"


def test_zombie_counts_as_stopped(tmp_path):
    ready = tmp_path / "ready"
    child = subprocess.Popen([sys.executable, "-c", GRACEFUL.format(delay=0), str(tmp_path / "cleaned"), str(ready)])
    try:
        wait_ready(ready)
        result, elapsed = run(tmp_path, child.pid, 5)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == f"stopped {child.pid} SIGTERM"
        assert elapsed < 4, "Tiến trình đã thành zombie (chờ cha gọi wait): nó đã chết, đừng chờ tới timeout"
    finally:
        child.kill()
        child.wait()


def owner(path: Path) -> int | None:
    try:
        return path.stat().st_uid
    except OSError:
        return None


def signal_denied(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return False


def test_not_permitted_process(tmp_path):
    """Chỉ dùng PID mà chính test đã thử và bị kernel từ chối: script (dù viết sai) cũng không gửi được signal nào."""
    if os.getuid() == 0:
        pytest.skip("Chạy bằng root thì không có tiến trình nào từ chối signal")
    candidates = (
        int(p.name)
        for p in Path("/proc").iterdir()
        if p.name.isdigit() and int(p.name) > 1 and owner(p) not in (None, os.getuid())
    )
    pid = next((c for c in candidates if signal_denied(c)), None)
    if pid is None:
        pytest.skip("Không có tiến trình nào từ chối signal của user này để thử")
    result, _ = run(tmp_path, pid, 1)
    assert result.returncode == 4
    assert result.stderr.strip()
    assert signal_denied(pid) or not Path(f"/proc/{pid}").exists()


def test_script_signalling_its_own_group_cannot_hit_pytest(tmp_path):
    script = tmp_path / "kill_group.sh"
    script.write_text('#!/usr/bin/env bash\necho "$HOME $LC_ALL ${VIRTUAL_ENV:-}"\nkill -TERM 0\necho survived\n')
    result, _ = run(tmp_path, 123, 1, script=script)
    assert result.returncode == -signal.SIGTERM
    assert result.stdout == f"{tmp_path} C.UTF-8 \n"
