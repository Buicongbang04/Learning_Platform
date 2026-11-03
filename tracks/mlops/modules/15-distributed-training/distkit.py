"""Tiện ích cho test module 15: chạy `torchrun` có timeout cứng và dọn sạch mọi tiến trình của lần chạy.

`torchrun` đặt mỗi worker vào một session riêng (`start_new_session=True`), nên giết process group của `torchrun` không
giết được worker đang treo trong collective gloo. Vì vậy mỗi lần chạy được gắn biến môi trường
`MLOPS_EX_DIST_RUN=<uuid8>`; worker, DataLoader worker và mọi tiến trình con kế thừa biến này, và `finally` diệt mọi
tiến trình mang đúng giá trị đó (chỉ của chính lần chạy, không theo tên chung).

Rendezvous là `c10d` trên `127.0.0.1:0` với `--local-addr=127.0.0.1`: cổng do hệ điều hành chọn (nhiều lần chạy song
song không giành cổng), mọi socket chỉ ở loopback (`GLOO_SOCKET_IFNAME=lo`). Không dùng `--standalone`: trên máy có
hostname phân giải ra IP LAN không định tuyến được, rendezvous `--standalone` treo.
"""

import os
import signal
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import pytest

MARKER = "MLOPS_EX_DIST_RUN"
LAUNCHER = ["-m", "torch.distributed.run", "--rdzv-backend=c10d", "--rdzv-endpoint=127.0.0.1:0",
            "--local-addr=127.0.0.1", "--max-restarts=0"]
QUIET_ENV = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "GLOO_SOCKET_IFNAME": "lo", "PYTHONUNBUFFERED": "1",
             "PYTHONDONTWRITEBYTECODE": "1"}


@dataclass
class Job:
    proc: subprocess.Popen
    run_id: str
    log: Path
    started: float = field(default_factory=time.monotonic)

    def output(self) -> str:
        return self.log.read_text(encoding="utf-8", errors="replace") if self.log.exists() else ""


@dataclass
class Run:
    returncode: int | None
    timed_out: bool
    seconds: float
    output: str
    leftover: list[int]

    @property
    def ok(self) -> bool:
        return not self.timed_out and self.returncode == 0

    def tail(self, lines: int = 40) -> str:
        return "\n".join(self.output.splitlines()[-lines:])


def marked(run_id: str) -> list[int]:
    """PID mọi tiến trình (của user hiện tại, đọc được environ) mang `MLOPS_EX_DIST_RUN=<run_id>`."""
    needle = b"\0" + f"{MARKER}={run_id}".encode() + b"\0"
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            environ = (entry / "environ").read_bytes()
        except OSError:
            continue
        if needle in b"\0" + environ.rstrip(b"\0") + b"\0":
            found.append(int(entry.name))
    return found


def kill_marked(run_id: str, rounds: int = 50) -> list[int]:
    """SIGKILL mọi tiến trình mang `run_id` cho tới khi không còn; trả PID còn sót sau `rounds` lượt (thường rỗng)."""
    for _ in range(rounds):
        pids = marked(run_id)
        if not pids:
            return []
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        time.sleep(0.1)
    return marked(run_id)


def command(script: Path, args: list, nproc: int) -> list[str]:
    return [sys.executable, *LAUNCHER, f"--nproc_per_node={nproc}", str(script), *map(str, args)]


@contextmanager
def launched(script: Path, args: list = (), *, workdir: Path, nproc: int = 2,
             extra_env: dict[str, str] | None = None) -> Iterator[Job]:
    """Chạy `torchrun` nền (session mới, output ghi tệp, không PIPE); `finally` diệt cả group lẫn mọi worker của lần chạy."""
    if not Path(script).is_file():
        pytest.fail(f"Không thấy script {script}", pytrace=False)
    run_id = uuid.uuid4().hex[:8]
    workdir.mkdir(parents=True, exist_ok=True)
    log = workdir / f"torchrun-{run_id}.log"
    env = {**os.environ, **QUIET_ENV, **(extra_env or {}), MARKER: run_id}
    with open(log, "wb") as out:
        proc = subprocess.Popen(command(Path(script), list(args), nproc), stdout=out, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, env=env, cwd=workdir, start_new_session=True)
    job = Job(proc, run_id, log)
    try:
        yield job
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        kill_marked(run_id)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass


def torchrun(script: Path, args: list = (), *, workdir: Path, timeout: float, nproc: int = 2,
             extra_env: dict[str, str] | None = None) -> Run:
    """Chạy `torchrun --nproc_per_node=nproc script args` tới khi xong hoặc hết `timeout` giây (khi đó diệt tất cả)."""
    with launched(script, args, workdir=workdir, nproc=nproc, extra_env=extra_env) as job:
        try:
            returncode, timed_out = job.proc.wait(timeout=timeout), False
        except subprocess.TimeoutExpired:
            returncode, timed_out = None, True
        seconds = time.monotonic() - job.started
    return Run(returncode, timed_out, seconds, job.output(), marked(job.run_id))


def wait_until(predicate, timeout: float, job: Job | None = None, interval: float = 0.05) -> bool:
    """Chờ `predicate()` đúng; dừng sớm (trả False) nếu `job` đã thoát trước đó."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        if job is not None and job.proc.poll() is not None:
            return bool(predicate())
        time.sleep(interval)
    return False


def pickle_by_value(module) -> None:
    """Module nạp bằng `ex.module` có tên riêng trong `sys.modules`; Ray worker không import được tên đó nên gửi theo giá trị."""
    import ray.cloudpickle

    ray.cloudpickle.register_pickle_by_value(module)
