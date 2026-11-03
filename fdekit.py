"""Công cụ dùng chung cho track Forward Deployed Engineer: VM "khách hàng" QEMU/KVM dựng từ cloud image chính thức,
seed cloud-init NoCloud, SSH bằng key riêng của từng lần chạy, snapshot nối tiếp và dọn theo run id."""
from __future__ import annotations

import argparse
import atexit
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping, Sequence

import pytest
import yaml

import testkit

ROOT = testkit.ROOT
RAW = ROOT / "data" / "raw"
CACHE = RAW / "fde-images"
LAB = ROOT / ".fde-lab"
PREFIX = "fde-ex-"
QEMU = "qemu-system-x86_64"
SSH_WAIT = 120
KVM_SKIP = "Cần /dev/kvm đọc/ghi được và qemu-system-x86_64 (cùng qemu-img). Xem setup/fde/README.md"
CAPSTONE_SKIP = "Đặt FDE_CAPSTONE_DIR=<đường dẫn repo capstone của bạn> trong setup/.env"
_RUN_ID = re.compile(r"^[0-9a-f]{8}$")
_GUARD = "--fdekit-guard"
_PORT_TAKEN = "Could not set up host forwarding rule"

testkit._load_env_file(ROOT / "setup" / ".env")


@dataclass(frozen=True)
class CloudImage:
    url: str
    sha256: str
    os_id: str
    os_version: str

    @property
    def filename(self) -> str:
        return self.url.rsplit("/", 1)[-1]


IMAGES: dict[str, CloudImage] = {
    "ubuntu-22.04": CloudImage(
        "https://cloud-images.ubuntu.com/releases/22.04/release-20261004/ubuntu-22.04-server-cloudimg-amd64.img",
        "012d81fade7e8ff4428fc35dfeee711d66d1f47d5ea9c5c8ced96a85b959835c",
        "ubuntu",
        "22.04",
    ),
    "ubuntu-20.04": CloudImage(
        "https://cloud-images.ubuntu.com/releases/focal/release-20250624/ubuntu-20.04-server-cloudimg-amd64.img",
        "18f2977d77dfea1b74aee14533bd21c34f789139e949c57023b7364894b7e5e9",
        "ubuntu",
        "20.04",
    ),
    "rocky-8": CloudImage(
        "https://dl.rockylinux.org/pub/rocky/8/images/x86_64/Rocky-8-GenericCloud-Base-8.10-20240528.0.x86_64.qcow2",
        "e56066c58606191e96184de9a9183a3af33c59bcbd8740d8b10ca054a7a89c14",
        "rocky",
        "8.10",
    ),
    "debian-12": CloudImage(
        "https://cloud.debian.org/images/cloud/bookworm/20261018-2635/debian-12-genericcloud-amd64-20261018-2635.qcow2",
        "c0a478483fb1a6c098b79edd27e6ec25db63dd359896e87dcf5c91e07b5fd503",
        "debian",
        "12",
    ),
}


def require_kvm() -> None:
    if not os.access("/dev/kvm", os.R_OK | os.W_OK) or not shutil.which(QEMU) or not shutil.which("qemu-img"):
        pytest.skip(KVM_SKIP)


def _require_ssh_tools() -> None:
    missing = [tool for tool in ("ssh", "scp", "ssh-keygen") if not shutil.which(tool)]
    if missing:
        pytest.skip(f"Thiếu {', '.join(missing)} (gói openssh-client)")


def _require_memory(memory_mb: int) -> None:
    try:
        meminfo = Path("/proc/meminfo").read_text()
    except OSError:
        return
    match = re.search(r"^MemAvailable:\s+(\d+) kB", meminfo, re.M)
    if match and int(match.group(1)) // 1024 < memory_mb + 512:
        pytest.skip(f"Không đủ RAM trống cho VM {memory_mb} MB (còn {int(match.group(1)) // 1024} MB). Đóng bớt ứng dụng rồi chạy lại")


def _download(url: str, dest: Path) -> None:
    import requests

    print(f"Đang tải {url} → {dest}", file=sys.stderr, flush=True)
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                handle.write(chunk)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stamp(path: Path, sha256: str) -> str:
    stat = path.stat()
    return f"{sha256} {stat.st_size} {stat.st_mtime_ns}"


def _verified(path: Path, sha256: str) -> bool:
    if not path.is_file():
        return False
    marker = path.with_name(path.name + ".sha256")
    if marker.is_file() and marker.read_text().strip() == _stamp(path, sha256):
        return True
    if _sha256(path) != sha256:
        return False
    marker.write_text(_stamp(path, sha256))
    return True


def fetch_image(name: str) -> Path:
    """Tải cloud image đã ghim vào CACHE (một lần), kiểm sha256; tệp sai hay hỏng thì tải lại."""
    image = IMAGES[name]
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / image.filename
    with (CACHE / f".{image.filename}.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if _verified(path, image.sha256):
            return path
        part = path.with_name(path.name + ".part")
        try:
            _download(image.url, part)
            actual = _sha256(part)
            if actual != image.sha256:
                raise RuntimeError(f"sha256 của {image.url} không khớp: cần {image.sha256}, nhận {actual}")
            os.replace(part, path)
        finally:
            part.unlink(missing_ok=True)
        path.with_name(path.name + ".sha256").write_text(_stamp(path, image.sha256))
    return path


def golden_path(profile: str) -> Path:
    return CACHE / "golden" / f"{profile}.qcow2"


def require_golden(profile: str) -> Path:
    require_kvm()
    path = golden_path(profile)
    if not path.is_file():
        pytest.skip(f"Chưa có golden image của hồ sơ khách '{profile}'. Chạy một lần: uv run python -m fdekit prepare {profile}")
    return path


def prepare(profile: str, *, force: bool = False) -> Path:
    raise NotImplementedError(f"Chưa dựng được golden image '{profile}': danh mục hồ sơ khách chưa được thêm vào fdekit")


def capstone_dir() -> Path:
    if testkit.use_solution():
        return ROOT / "tracks" / "fde" / "capstone" / "solutions" / "project"
    value = os.environ.get("FDE_CAPSTONE_DIR", "").strip()
    if not value:
        pytest.skip(CAPSTONE_SKIP)
    path = Path(value).expanduser()
    if not path.is_dir():
        pytest.skip(f"FDE_CAPSTONE_DIR={value} không phải thư mục. {CAPSTONE_SKIP}")
    return path


def generate_key(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", path.parent.name or "fde-lab", "-f", str(path)],
        check=True, capture_output=True, stdin=subprocess.DEVNULL,
    )
    path.chmod(0o600)
    return path


def write_seed_iso(path: Path, *, instance_id: str, public_key: str, user: str = "fde", sudo: bool = False,
                   cloud_config: Mapping | None = None) -> Path:
    """Seed NoCloud (ISO nhãn `cidata`): tạo user với key công khai của lần chạy; không chứa khoá riêng hay mật khẩu."""
    account = {"name": user, "shell": "/bin/bash", "lock_passwd": True, "ssh_authorized_keys": [public_key]}
    if sudo:
        account["sudo"] = "ALL=(ALL) NOPASSWD:ALL"
    config = {"users": [account], "ssh_pwauth": False, "disable_root": True, **(cloud_config or {})}
    files = {
        "user-data": "#cloud-config\n" + yaml.safe_dump(config, sort_keys=False, width=1 << 16),
        "meta-data": yaml.safe_dump({"instance-id": instance_id, "local-hostname": instance_id}),
    }
    import pycdlib

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, joliet=3, rock_ridge="1.09", vol_ident="cidata")
    for name, text in files.items():
        data = text.encode()
        iso.add_fp(io.BytesIO(data), len(data), f"/{name.replace('-', '').upper()}.;1", rr_name=name, joliet_path=f"/{name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    iso.write(str(path))
    iso.close()
    return path


def _netdev(*, ssh_port: int, forwards: Mapping[int, int], guestfwds: Mapping[str, int], restrict: bool) -> str:
    parts = ["user", "id=n0", f"restrict={'on' if restrict else 'off'}", f"hostfwd=tcp:127.0.0.1:{ssh_port}-:22"]
    parts += [f"hostfwd=tcp:127.0.0.1:{host}-:{guest}" for guest, host in forwards.items()]
    parts += [f"guestfwd=tcp:{target}-tcp:127.0.0.1:{host}" for target, host in guestfwds.items()]
    return ",".join(parts)


def _opt(path: Path) -> str:
    return str(path).replace(",", ",,")


_WRAPPER = r"""
import ctypes, os, shutil, signal, subprocess, sys
parent, run_dir, cmd = int(sys.argv[2]), sys.argv[3], sys.argv[4:]
libc = ctypes.CDLL(None, use_errno=True)
state = {"proc": None}
def stop(signum, frame):
    proc = state["proc"]
    if proc is not None:
        try:
            os.kill(proc.pid, signal.SIGKILL)
            os.waitpid(proc.pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
    shutil.rmtree(run_dir, ignore_errors=True)
    os._exit(143)
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGHUP, stop)
libc.prctl(1, signal.SIGTERM)
if os.getppid() != parent:
    stop(None, None)
me = os.getpid()
def child():
    libc.prctl(1, signal.SIGKILL)
    if os.getppid() != me:
        os._exit(1)
state["proc"] = subprocess.Popen(cmd, preexec_fn=child, stdin=subprocess.DEVNULL)
sys.exit(state["proc"].wait())
"""


class _PortTaken(Exception):
    pass


def _tail(path: Path, lines: int = 30) -> str:
    try:
        return "\n".join(path.read_text(errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


class VM:
    """VM đang chạy của một lần chạy. Chỉ lấy qua `with fdekit.vm(...) as m:`."""

    def __init__(self, run_id: str, run_dir: Path, ssh_port: int, ports: Mapping[int, int]) -> None:
        self.run_id = run_id
        self.name = PREFIX + run_id
        self.dir = run_dir
        self.key = run_dir / "id_ed25519"
        self.overlay = run_dir / "disk.qcow2"
        self.ssh_port = ssh_port
        self._ports = dict(ports)
        self._guard: subprocess.Popen | None = None

    def _options(self) -> list[str]:
        return [
            "-F", "/dev/null", "-i", str(self.key),
            "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null", "-o", "GlobalKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=10",
        ]

    def ssh_command(self, user: str = "fde") -> list[str]:
        return ["ssh", *self._options(), "-p", str(self.ssh_port), f"{user}@127.0.0.1"]

    def ssh(self, cmd: str, *, user: str = "fde", timeout: float = 60, check: bool = False) -> subprocess.CompletedProcess:
        result = subprocess.run([*self.ssh_command(user), cmd], capture_output=True, text=True, timeout=timeout,
                                stdin=subprocess.DEVNULL)
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        return result

    def _scp(self, source: str, target: str) -> None:
        result = subprocess.run(["scp", "-q", "-r", *self._options(), "-P", str(self.ssh_port), source, target],
                                capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            raise RuntimeError(f"scp {source} → {target} lỗi ({result.returncode}): {result.stderr.strip()}")

    def put(self, local: Path, remote: str) -> None:
        self._scp(str(local), f"fde@127.0.0.1:{remote}")

    def get(self, remote: str, local: Path) -> None:
        self._scp(f"fde@127.0.0.1:{remote}", str(local))

    def port(self, guest_port: int) -> int:
        if guest_port not in self._ports:
            raise KeyError(f"Cổng {guest_port} của VM chưa được forward; thêm vào vm(..., forwards=({guest_port},))")
        return self._ports[guest_port]

    def _start(self, args: list[str]) -> None:
        log = (self.dir / "qemu.log").open("ab")
        try:
            self._guard = subprocess.Popen(
                [sys.executable, "-I", "-c", _WRAPPER, _GUARD, str(os.getpid()), str(self.dir), *args],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
        finally:
            log.close()

    def _running(self) -> bool:
        return self._guard is not None and self._guard.poll() is None

    def _wait_ssh(self, timeout: float = SSH_WAIT) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self._running():
                log = _tail(self.dir / "qemu.log")
                if _PORT_TAKEN in log:
                    raise _PortTaken(log)
                raise RuntimeError(f"QEMU của {self.name} dừng khi đang boot:\n{log}")
            try:
                if self.ssh("true", timeout=15).returncode == 0:
                    return
            except subprocess.TimeoutExpired:
                pass
            time.sleep(1)
        raise RuntimeError(
            f"VM {self.name} không mở SSH sau {timeout:.0f} s.\nqemu.log:\n{_tail(self.dir / 'qemu.log')}\n"
            f"console.log:\n{_tail(self.dir / 'console.log')}"
        )

    def _qmp(self, command: str) -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(10)
            sock.connect(str(self.dir / "qmp.sock"))
            stream = sock.makefile("rwb")
            stream.readline()
            for execute in ("qmp_capabilities", command):
                stream.write(json.dumps({"execute": execute}).encode() + b"\n")
                stream.flush()
                while True:
                    reply = json.loads(stream.readline() or b"{}")
                    if not reply or "return" in reply or "error" in reply:
                        break

    def shutdown(self, timeout: float = 180) -> None:
        """Tắt sạch bằng nút nguồn ACPI (không cần sudo trong VM), chờ QEMU thoát."""
        deadline = time.monotonic() + timeout
        while self._running() and time.monotonic() < deadline:
            try:
                self._qmp("system_powerdown")
            except OSError:
                pass
            try:
                self._guard.wait(timeout=min(20, max(1, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                pass
        if self._running():
            raise RuntimeError(f"VM {self.name} không tắt sau {timeout:.0f} s")

    def snapshot(self, path: Path) -> None:
        """Tắt sạch VM rồi ghi đĩa hiện tại thành qcow2 độc lập (không còn backing file). VM không dùng tiếp được."""
        self.shutdown()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        try:
            subprocess.run(["qemu-img", "convert", "-O", "qcow2", str(self.overlay), str(part)],
                           check=True, capture_output=True, text=True)
            os.replace(part, path)
        finally:
            part.unlink(missing_ok=True)

    def _stop(self) -> None:
        if self._running():
            self._guard.terminate()
            try:
                self._guard.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self._guard.kill()
                self._guard.wait()


_ACTIVE: set[str] = set()


def _cleanup_active() -> None:
    for run_id in list(_ACTIVE):
        clean(run_id)


atexit.register(_cleanup_active)


def _image_format(path: Path) -> str:
    result = subprocess.run(["qemu-img", "info", "--output=json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)["format"]


def _qemu_args(machine: VM, *, base_seed: Path, memory_mb: int, cpus: int, netdev: str) -> list[str]:
    return [
        QEMU, "-name", f"{machine.name},process={machine.name}",
        "-machine", "q35,accel=kvm", "-cpu", "host", "-smp", str(cpus), "-m", str(memory_mb),
        "-nodefaults", "-no-user-config", "-display", "none",
        "-serial", f"file:{_opt(machine.dir / 'console.log')}",
        "-drive", f"file={_opt(machine.overlay)},if=virtio,format=qcow2,discard=unmap",
        "-drive", f"file={_opt(base_seed)},if=virtio,format=raw,readonly=on",
        "-netdev", netdev, "-device", "virtio-net-pci,netdev=n0",
        "-device", "virtio-rng-pci",
        "-qmp", f"unix:{_opt(machine.dir / 'qmp.sock')},server=on,wait=off",
        "-pidfile", str(machine.dir / "qemu.pid"),
    ]


@contextmanager
def vm(profile: str | None, *, memory_mb: int = 2048, cpus: int = 2, forwards: Sequence[int] = (),
       guestfwds: Mapping[str, int] = {}, base: Path | None = None, restrict: bool = False, sudo: bool = False,
       cloud_config: Mapping | None = None) -> Iterator[VM]:
    """Boot một VM từ overlay qcow2 trên golden của `profile` (hoặc trên `base`), chờ SSH rồi trả `VM`; luôn dọn khi ra.

    `guestfwds` ánh xạ "ip:port" phía VM → cổng 127.0.0.1 phía host; `restrict=True` cắt mọi đường ra ngoài trừ forward.
    """
    require_kvm()
    _require_ssh_tools()
    _require_memory(memory_mb)
    if base is None:
        if profile is None:
            raise ValueError("vm() cần profile hoặc base")
        base = require_golden(profile)
    base = Path(base).resolve()
    if not base.is_file():
        raise FileNotFoundError(base)
    run_id = uuid.uuid4().hex[:8]
    run_dir = LAB / f"{PREFIX}{run_id}"
    if len(str(run_dir / "qmp.sock")) > 100:
        raise RuntimeError(f"Đường dẫn repo quá dài cho unix socket của QEMU ({run_dir}); clone repo vào thư mục ngắn hơn")
    _ACTIVE.add(run_id)
    machine: VM | None = None
    try:
        run_dir.mkdir(parents=True, mode=0o700)
        key = generate_key(run_dir / "id_ed25519")
        seed = write_seed_iso(run_dir / "seed.iso", instance_id=f"{PREFIX}{run_id}",
                              public_key=key.with_name(key.name + ".pub").read_text().strip(), sudo=sudo,
                              cloud_config=cloud_config)
        subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", "-F", _image_format(base), "-b", str(base),
                        str(run_dir / "disk.qcow2")], check=True, capture_output=True, text=True)
        for attempt in range(3):
            ports = {int(guest): testkit.free_port() for guest in forwards}
            machine = VM(run_id, run_dir, testkit.free_port(), ports)
            netdev = _netdev(ssh_port=machine.ssh_port, forwards=ports, guestfwds=guestfwds, restrict=restrict)
            machine._start(_qemu_args(machine, base_seed=seed, memory_mb=memory_mb, cpus=cpus, netdev=netdev))
            try:
                machine._wait_ssh()
                break
            except _PortTaken:
                machine._stop()
                if attempt == 2:
                    raise RuntimeError(f"Không tìm được cổng trống cho {machine.name} sau 3 lần thử")
        yield machine
    finally:
        if machine is not None:
            machine._stop()
        clean(run_id)
        _ACTIVE.discard(run_id)


def _processes(needle: str) -> list[tuple[int, bool, str]]:
    found = []
    uid = os.getuid()
    me = os.getpid()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == me:
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        args = [a.decode(errors="replace") for a in argv if a]
        if not args or not any(needle in a for a in args):
            continue
        if Path(args[0]).name.startswith("qemu-system"):
            found.append((int(entry.name), False, " ".join(args)[:160]))
        elif _GUARD in args:
            found.append((int(entry.name), True, " ".join(args[args.index(_GUARD):])[:160]))
    return found


def _qemu_pids(run_id: str) -> list[int]:
    return [pid for pid, guard, _ in _processes(f"{PREFIX}{run_id}") if not guard]


def _containers(needle: str) -> list[str]:
    if not shutil.which("docker"):
        return []
    try:
        result = subprocess.run(["docker", "ps", "-a", "--filter", f"name={needle}", "--format", "{{.Names}}"],
                                capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        return []
    return [name for name in result.stdout.split() if name.startswith(needle)] if result.returncode == 0 else []


def leftovers(run_id: str | None = None) -> list[str]:
    """Tiến trình QEMU, thư mục lab (overlay, seed, key) và container còn sót. `run_id=None` chỉ để báo cáo."""
    needle = f"{PREFIX}{run_id}" if run_id else PREFIX
    found = [f"process {pid}: {line}" for pid, _, line in _processes(needle)]
    if LAB.is_dir():
        found += sorted(str(path) for path in LAB.iterdir() if path.name.startswith(needle))
    found += [f"container {name}" for name in _containers(needle)]
    return found


def clean(run_id: str) -> None:
    """Dọn mọi thứ của đúng một run id: tiến trình QEMU, thư mục lab, container `fde-ex-<run_id>*`."""
    if not _RUN_ID.match(run_id or ""):
        raise ValueError(f"run id phải là 8 ký tự hex, nhận {run_id!r}")
    needle = f"{PREFIX}{run_id}"
    for sig, wait in ((signal.SIGTERM, 5.0), (signal.SIGKILL, 5.0)):
        pids = [pid for pid, _, _ in _processes(needle)]
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + wait
        while pids and _processes(needle) and time.monotonic() < deadline:
            time.sleep(0.1)
    shutil.rmtree(LAB / needle, ignore_errors=True)
    names = _containers(needle)
    if names:
        subprocess.run(["docker", "rm", "-f", *names], capture_output=True, timeout=60)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m fdekit", description="VM khách hàng cho track FDE")
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="dựng golden image của một hồ sơ khách")
    prep.add_argument("profile")
    prep.add_argument("--force", action="store_true")
    commands.add_parser("leftovers", help="liệt kê tiến trình QEMU, overlay, container fde-ex-* còn sót")
    cleaner = commands.add_parser("clean", help="dọn mọi thứ của một run id")
    cleaner.add_argument("run_id")
    args = parser.parse_args(argv)
    if args.command == "prepare":
        try:
            print(prepare(args.profile, force=args.force))
        except NotImplementedError as error:
            print(error, file=sys.stderr)
            return 2
        return 0
    if args.command == "clean":
        try:
            clean(args.run_id)
        except ValueError as error:
            print(error, file=sys.stderr)
            return 2
    remaining = leftovers(getattr(args, "run_id", None))
    print("\n".join(remaining) if remaining else "Không còn gì sót lại")
    return 0


if __name__ == "__main__":
    sys.exit(main())
