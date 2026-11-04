"""Kiểm helper `distkit`: job torchrun không mở socket ra mạng của máy, và dọn chỉ đúng tiến trình của lần chạy."""

import os
import re
import subprocess
from pathlib import Path

import distkit
import pytest

SLEEPER = Path(__file__).parent / "fixtures" / "sleeper.py"
SOCKET = re.compile(r"socket:\[(\d+)\]")


def host_listening_inodes() -> set[str]:
    inodes = set()
    for table in ("tcp", "tcp6"):
        for line in Path(f"/proc/self/net/{table}").read_text().splitlines()[1:]:
            fields = line.split()
            if fields[3] == "0A":
                inodes.add(fields[9])
    return inodes


def socket_inodes(pid: int) -> set[str]:
    found = set()
    try:
        for fd in Path(f"/proc/{pid}/fd").iterdir():
            match = SOCKET.match(os.readlink(fd))
            if match:
                found.add(match.group(1))
    except OSError:
        pass
    return found


def test_job_sockets_are_not_reachable_from_the_host_network(tmp_path):
    if not distkit.isolated():
        pytest.skip("Máy không cho tạo user namespace không cần root: torchrun chạy không cô lập mạng (README module mục 0)")
    with distkit.launched(SLEEPER, [tmp_path], workdir=tmp_path) as job:
        ready = distkit.wait_until(lambda: all((tmp_path / f"ready{r}").exists() for r in (0, 1)), 120, job)
        assert ready, job.output()[-2000:]
        pids = distkit.marked(job.run_id)
        assert len(pids) >= 3
        own = os.readlink("/proc/self/ns/net")
        assert all(os.readlink(f"/proc/{pid}/ns/net") != own for pid in pids)
        exposed = host_listening_inodes() & set().union(*(socket_inodes(pid) for pid in pids))
        assert not exposed, "Job có socket LISTEN trong network namespace của máy"
        run_id = job.run_id
    assert distkit.marked(run_id) == []


def test_cleanup_leaves_other_processes_alone(tmp_path):
    bystander = subprocess.Popen(["sleep", "30"])
    try:
        with distkit.launched(SLEEPER, [tmp_path], workdir=tmp_path) as job:
            distkit.wait_until(lambda: (tmp_path / "ready0").exists(), 120, job)
        assert bystander.poll() is None
        assert distkit.kill_marked("deadbeef") == []
        assert bystander.poll() is None
    finally:
        bystander.kill()
        bystander.wait()
