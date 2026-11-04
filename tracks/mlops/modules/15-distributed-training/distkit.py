"""Tiện ích cho test module 15: chạy `torchrun` có timeout cứng và dọn sạch mọi tiến trình của lần chạy.

`torchrun` đặt mỗi worker vào một session riêng (`start_new_session=True`), nên giết process group của `torchrun` không
giết được worker đang treo trong collective gloo. Vì vậy mỗi lần chạy được gắn biến môi trường
`MLOPS_EX_DIST_RUN=<uuid8>`; worker, DataLoader worker và mọi tiến trình con kế thừa biến này, và `finally` diệt mọi
tiến trình mang đúng giá trị đó (chỉ của chính lần chạy, không theo tên chung).

Rendezvous là `c10d` trên `127.0.0.1:0` với `--local-addr=127.0.0.1`: cổng do hệ điều hành chọn (nhiều lần chạy song
song không giành cổng). Không dùng `--standalone`: trên máy có hostname phân giải ra IP LAN không định tuyến được,
rendezvous `--standalone` treo.

Cô lập mạng: gloo nghe 127.0.0.1 (`GLOO_SOCKET_IFNAME=lo`), nhưng TCPStore của chính `torchrun` (rendezvous c10d và
store của agent) nghe `*:<cổng>` (mọi interface, IPv4 và IPv6, không xác thực) và torch 2.14.1 không có cờ hay biến môi
trường nào ép nó về loopback (đã kiểm bằng `ss -tlnp`). Vì vậy khi máy cho phép user namespace không cần root,
`torchrun` chạy trong network namespace riêng (`unshare --user --map-root-user --net`, bật `lo`): mọi socket của job
chỉ tồn tại trong namespace đó, từ ngoài không kết nối được. Máy chặn user namespace (vd. AppArmor của Ubuntu 24.04
`kernel.apparmor_restrict_unprivileged_userns=1`) thì chạy không cô lập và `isolated()` trả False.
"""

import functools
import os
import shutil
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
NETNS = ["unshare", "--user", "--map-root-user", "--net", "--", "sh", "-c", 'ip link set lo up && exec "$@"', "sh"]
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


def _has_marker(pid: int, needle: bytes) -> bool:
    try:
        environ = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return False
    return needle in b"\0" + environ.rstrip(b"\0") + b"\0"


def _needle(run_id: str) -> bytes:
    return b"\0" + f"{MARKER}={run_id}".encode() + b"\0"


def marked(run_id: str) -> list[int]:
    """PID mọi tiến trình (của user hiện tại, đọc được environ) mang `MLOPS_EX_DIST_RUN=<run_id>`."""
    needle = _needle(run_id)
    return [int(e.name) for e in Path("/proc").iterdir() if e.name.isdigit() and _has_marker(int(e.name), needle)]


def _kill(pid: int, needle: bytes) -> None:
    """Giữ pidfd trước, đọc lại environ qua đúng tiến trình đó rồi mới gửi tín hiệu: PID bị tái sử dụng không bị giết nhầm."""
    try:
        fd = os.pidfd_open(pid)
    except OSError:
        return
    try:
        if _has_marker(pid, needle):
            signal.pidfd_send_signal(fd, signal.SIGKILL)
    except OSError:
        pass
    finally:
        os.close(fd)


def kill_marked(run_id: str, rounds: int = 50) -> list[int]:
    """SIGKILL mọi tiến trình mang `run_id` cho tới khi không còn; trả PID còn sót sau `rounds` lượt (thường rỗng)."""
    needle = _needle(run_id)
    for _ in range(rounds):
        pids = marked(run_id)
        if not pids:
            return []
        for pid in pids:
            _kill(pid, needle)
        time.sleep(0.1)
    return marked(run_id)


@functools.cache
def _netns_prefix() -> tuple[str, ...]:
    if not (shutil.which("unshare") and shutil.which("ip")):
        return ()
    try:
        probe = subprocess.run([*NETNS, "true"], capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ()
    return tuple(NETNS) if probe.returncode == 0 else ()


def isolated() -> bool:
    """True nếu job torchrun chạy trong network namespace riêng (mọi socket của job không lộ ra ngoài máy)."""
    return bool(_netns_prefix())


def command(script: Path, args: list, nproc: int) -> list[str]:
    return [*_netns_prefix(), sys.executable, *LAUNCHER, f"--nproc_per_node={nproc}", str(script), *map(str, args)]


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
        if proc.poll() is None:
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
