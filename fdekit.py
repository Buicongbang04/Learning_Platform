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
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal, Mapping, Sequence

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


SETUP = ROOT / "setup" / "fde"
PROFILE_DIR = SETUP / "profiles"
SCRIPT_DIR = SETUP / "cloud-init"
SITE_MEMORY_MB = 2048
SITE_CPUS = 2
PROXY_ADDR = "10.0.2.100:3128"
REGISTRY_ADDR = "10.0.2.101:5000"
MITMPROXY_IMAGE = "mitmproxy/mitmproxy:12.2.3@sha256:00b77b5d8804c8ad18cb6caefbf9d5849e895e8986c5ce011f4ae30f4385962f"
REGISTRY_IMAGE = "registry:2.8.3@sha256:a3d8aaa63ed8681a604f1dea0aa03f100d5895b6a58ace528858a7b332415373"
SITE_IMAGES = {"proxy": MITMPROXY_IMAGE, "registry": REGISTRY_IMAGE}

Egress = Literal["open", "proxy", "none"]
SELinux = Literal["enforcing", "permissive", "disabled", "n/a"]
Runtime = Literal["docker", "podman", "k3s", "none"]
Service = Literal["proxy", "registry"]
_CHOICES = {
    "egress": ("open", "proxy", "none"),
    "selinux": ("enforcing", "permissive", "disabled", "n/a"),
    "runtime": ("docker", "podman", "k3s", "none"),
}
_MEASURED_FACTS = ("kernel_major", "glibc", "disk_free_gb_max", "gpu")


@dataclass(frozen=True)
class Profile:
    """Hồ sơ khách (setup/fde/profiles/<name>.yaml). `facts` là sự thật để chấm báo cáo survey: kernel_major, glibc,
    disk_free_gb_max, gpu đo trên golden; cpus/mem_mb là cấu hình `customer_site` mặc định boot; còn lại suy từ hồ sơ."""

    name: str
    image: str
    disk_gb: int
    sudo: bool
    egress: Egress
    tls_inspection: bool
    selinux: SELinux
    runtime: Runtime
    services: list[Service] = field(default_factory=list)
    facts: dict = field(default_factory=dict)


def _load_profile(path: Path) -> Profile:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key, allowed in _CHOICES.items():
        if data[key] not in allowed:
            raise ValueError(f"{path}: {key}={data[key]!r} không thuộc {allowed}")
    if data["image"] not in IMAGES:
        raise ValueError(f"{path}: image {data['image']!r} không có trong IMAGES")
    services = list(data.get("services") or [])
    if not set(services) <= {"proxy", "registry"} or ("proxy" in services) != (data["egress"] == "proxy"):
        raise ValueError(f"{path}: services {services} không khớp egress {data['egress']}")
    if data.get("tls_inspection", False) and data["egress"] != "proxy":
        raise ValueError(f"{path}: tls_inspection chỉ dùng với egress proxy")
    measured = data.get("facts") or {}
    missing = [key for key in _MEASURED_FACTS if key not in measured]
    if missing:
        raise ValueError(f"{path}: facts thiếu {missing}")
    for key in ("kernel_major", "glibc"):
        if not isinstance(measured[key], str):
            raise ValueError(f"{path}: facts.{key} phải là chuỗi có ngoặc kép (vd. \"5.10\"), nhận {measured[key]!r}")
    if not int(measured["disk_free_gb_max"]) < int(data["disk_gb"]):
        raise ValueError(f"{path}: facts.disk_free_gb_max phải nhỏ hơn disk_gb")
    image = IMAGES[data["image"]]
    facts = {
        "os_id": image.os_id,
        "os_version": image.os_version,
        "kernel_major": measured["kernel_major"],
        "glibc": measured["glibc"],
        "cpus": SITE_CPUS,
        "mem_mb": SITE_MEMORY_MB,
        "disk_free_gb_max": int(measured["disk_free_gb_max"]),
        "gpu": measured["gpu"],
        "proxy_url": f"http://{PROXY_ADDR}" if data["egress"] == "proxy" else None,
        "sudo": bool(data["sudo"]),
        "selinux": data["selinux"],
        "runtime": data["runtime"],
        "egress": data["egress"],
    }
    return Profile(name=path.stem, image=data["image"], disk_gb=int(data["disk_gb"]), sudo=bool(data["sudo"]),
                   egress=data["egress"], tls_inspection=bool(data.get("tls_inspection", False)),
                   selinux=data["selinux"], runtime=data["runtime"], services=services, facts=facts)


PROFILES: dict[str, Profile] = {path.stem: _load_profile(path) for path in sorted(PROFILE_DIR.glob("*.yaml"))}


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


def prepare_script(profile: str) -> Path:
    return SCRIPT_DIR / f"{profile}.sh"


class UnknownProfile(KeyError):
    pass


def _profile(name: str) -> Profile:
    if name not in PROFILES:
        raise UnknownProfile(f"Không có hồ sơ khách '{name}'. Có: {', '.join(sorted(PROFILES))}")
    return PROFILES[name]


def _pull_site_images(spec: Profile) -> None:
    for service in spec.services:
        image = SITE_IMAGES[service]
        if not shutil.which("docker"):
            print(f"Chưa có docker: cài Docker rồi chạy docker pull {image}", file=sys.stderr)
            continue
        if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0:
            continue
        print(f"docker pull {image}", file=sys.stderr, flush=True)
        if subprocess.run(["docker", "pull", "-q", image], capture_output=True, text=True).returncode != 0:
            print(f"Không pull được {image}; chạy lại: docker pull {image}", file=sys.stderr)


def prepare(profile: str, *, force: bool = False) -> Path:
    """Dựng golden image của hồ sơ khách: boot cloud image có mạng (restrict tắt, user `fde` có sudo tạm), chạy
    setup/fde/cloud-init/<hồ sơ>.sh (cài runtime, cấu hình "tật", gỡ sudo tạm, xoá key), tắt sạch rồi ghi qcow2 độc lập.
    Golden đã có thì trả luôn, trừ khi `force`. Kèm theo pull image proxy/registry phía host mà hồ sơ cần."""
    spec = _profile(profile)
    golden = _build_golden(spec, force=force)
    _pull_site_images(spec)
    return golden


def _build_golden(spec: Profile, *, force: bool) -> Path:
    profile = spec.name
    golden = golden_path(profile)
    if golden.is_file() and not force:
        return golden
    script = prepare_script(profile)
    if not script.is_file():
        raise FileNotFoundError(f"Thiếu script dựng golden {script}")
    require_kvm()
    _require_ssh_tools()
    _require_memory(SITE_MEMORY_MB)
    golden.parent.mkdir(parents=True, exist_ok=True)
    with (golden.parent / f".{profile}.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if golden.is_file() and not force:
            return golden
        base = fetch_image(spec.image)
        staging = golden.parent / f".{profile}.staging.qcow2"
        try:
            subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", "-F", _image_format(base), "-b", str(base),
                            str(staging), f"{spec.disk_gb}G"], check=True, capture_output=True, text=True)
            with vm(None, base=staging, memory_mb=SITE_MEMORY_MB, cpus=SITE_CPUS, restrict=False, sudo=True) as m:
                status = m.ssh("cloud-init status --wait --long", timeout=600)
                if status.returncode != 0 or "status: done" not in status.stdout:
                    raise RuntimeError(f"cloud-init của VM dựng golden '{profile}' không xong sạch "
                                       f"(mã {status.returncode}):\n{status.stdout}{status.stderr}")
                m.put(SCRIPT_DIR, "/tmp/fde-prepare")
                result = m.ssh(f"sudo bash /tmp/fde-prepare/{shlex.quote(profile)}.sh", timeout=1800)
                (golden.parent / f"{profile}.prepare.log").write_text(result.stdout + result.stderr)
                if result.returncode != 0:
                    raise RuntimeError(f"Script dựng golden '{profile}' lỗi ({result.returncode}):\n"
                                       f"{(result.stdout + result.stderr)[-3000:]}")
                m.snapshot(golden)
        finally:
            staging.unlink(missing_ok=True)
    return golden


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


_RESERVED_CLOUD_CONFIG = frozenset({"users", "user", "ssh_pwauth", "disable_root", "ssh_authorized_keys", "chpasswd", "password"})


def write_seed_iso(path: Path, *, instance_id: str, public_key: str, user: str = "fde", sudo: bool = False,
                   cloud_config: Mapping | None = None) -> Path:
    """Seed NoCloud (ISO nhãn `cidata`): tạo user với key công khai của lần chạy; không chứa khoá riêng hay mật khẩu."""
    account = {"name": user, "shell": "/bin/bash", "lock_passwd": True, "ssh_authorized_keys": [public_key]}
    if sudo:
        account["sudo"] = "ALL=(ALL) NOPASSWD:ALL"
    reserved = sorted(set(cloud_config or {}) & _RESERVED_CLOUD_CONFIG)
    if reserved:
        raise ValueError(f"cloud_config không được ghi đè {', '.join(reserved)} (user fde và key SSH của lần chạy do fdekit đặt)")
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


def _opt(path: Path | str) -> str:
    return str(path).replace(",", ",,")


_RELAY = r"""
import os, select, socket, sys
os.dup2(os.open(os.devnull, os.O_WRONLY), 2)
upstream = socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=10)
upstream.settimeout(None)
sources = [0, upstream]
while True:
    ready, _, _ = select.select(sources, [], [])
    if 0 in ready:
        data = os.read(0, 65536)
        if data:
            upstream.sendall(data)
        else:
            upstream.shutdown(socket.SHUT_WR)
            sources.remove(0)
    if upstream in ready:
        data = upstream.recv(65536)
        if not data:
            break
        view = memoryview(data)
        while view:
            view = view[os.write(1, view):]
"""


def _write_relay(run_dir: Path) -> Path:
    """Mỗi kết nối guestfwd, QEMU chạy một relay: stdin/stdout là socket phía VM, đầu kia là cổng 127.0.0.1 của host."""
    path = run_dir / _RELAY_NAME
    path.write_text(_RELAY)
    return path


def _netdev(*, ssh_port: int, forwards: Mapping[int, int], guestfwds: Mapping[str, int], restrict: bool,
            relay: Path | None = None) -> str:
    parts = ["user", "id=n0", f"restrict={'on' if restrict else 'off'}", f"hostfwd=tcp:127.0.0.1:{ssh_port}-:22"]
    parts += [f"hostfwd=tcp:127.0.0.1:{host}-:{guest}" for guest, host in forwards.items()]
    if guestfwds and relay is None:
        raise ValueError("guestfwds cần relay")
    for target, host in guestfwds.items():
        command = f"{shlex.quote(sys.executable)} -I {shlex.quote(str(relay))} 127.0.0.1 {int(host)}"
        parts.append(f"guestfwd=tcp:{target}-cmd:{_opt(command)}")
    return ",".join(parts)


_WRAPPER = r"""
import ctypes, json, os, select, shutil, signal, subprocess, sys, time
lifeline, run_dir = int(sys.argv[2]), sys.argv[3]
needle = os.path.basename(run_dir)
libc = ctypes.CDLL(None, use_errno=True)
state = {"proc": None, "halt": False}
def path(name):
    return os.path.join(run_dir, name)
def kill():
    proc = state["proc"]
    if proc is None:
        return
    try:
        os.kill(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()
    finished(proc)
def finished(proc):
    state["proc"] = None
    code = proc.returncode
    try:
        with open(path("qemu.exit.tmp"), "w") as handle:
            handle.write(str(code))
        os.replace(path("qemu.exit.tmp"), path("qemu.exit"))
    except OSError:
        pass
def docker(*args):
    try:
        result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    return result.stdout.split() if result.returncode == 0 else []
def mine(name):
    return name == needle or name.startswith(needle + "-")
def purge_docker():
    started = time.monotonic()
    while True:
        names = [n for n in docker("ps", "-a", "--filter", "name=" + needle, "--format", "{{.Names}}") if mine(n)]
        if names:
            docker("rm", "-f", *names)
        networks = [n for n in docker("network", "ls", "--filter", "name=" + needle, "--format", "{{.Name}}") if mine(n)]
        if networks:
            docker("network", "rm", *networks)
        elapsed = time.monotonic() - started
        if elapsed > 10 or (not names and not networks and elapsed > 4):
            return
        time.sleep(2)
def purge():
    kill()
    if os.path.exists(path("containers")) and shutil.which("docker"):
        purge_docker()
    shutil.rmtree(run_dir, ignore_errors=True)
    os._exit(0)
def stop(signum, frame):
    kill()
    os._exit(143)
def halt(signum, frame):
    state["halt"] = True
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGHUP, stop)
signal.signal(signal.SIGUSR1, halt)
me = os.getpid()
def child():
    libc.prctl(1, signal.SIGKILL)
    if os.getppid() != me:
        os._exit(1)
def launch():
    try:
        with open(path("qemu.start")) as handle:
            argv = json.load(handle)
        os.unlink(path("qemu.start"))
    except (OSError, ValueError):
        return
    with open(path("qemu.log"), "wb") as log:
        try:
            state["proc"] = subprocess.Popen(argv, preexec_fn=child, stdin=subprocess.DEVNULL, stdout=log,
                                             stderr=subprocess.STDOUT)
        except OSError as error:
            log.write(str(error).encode())
            state["proc"] = None
            with open(path("qemu.exit"), "w") as handle:
                handle.write("127")
while True:
    ready, _, _ = select.select([lifeline], [], [], 0.1)
    if ready and not os.read(lifeline, 1):
        purge()
    if state["halt"]:
        state["halt"] = False
        kill()
    proc = state["proc"]
    if proc is not None and proc.poll() is not None:
        finished(proc)
    if state["proc"] is None and os.path.exists(path("qemu.start")):
        launch()
"""


def _spawn_guard(run_dir: Path) -> subprocess.Popen:
    """Một tiến trình canh cho mỗi run id, giữ đầu đọc lifeline. Nó chạy QEMU (`VM._start` ghi `qemu.start`, QEMU thoát
    thì nó ghi `qemu.exit`), SIGUSR1 giết QEMU. Tiến trình gọi chết (kể cả SIGKILL) thì nó giết QEMU, xoá container/network
    `fde-ex-<run_id>*` (chỉ khi run có tệp đánh dấu `containers`, lặp tới ~10 s để bắt container đang tạo dở) và thư mục
    lab. SIGTERM (từ `clean`) chỉ giết QEMU rồi thoát; phần dọn do bên gọi làm."""
    lifeline = _lifeline()
    return subprocess.Popen(
        [sys.executable, "-I", "-c", _WRAPPER, _GUARD, str(lifeline), str(run_dir)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
        pass_fds=(lifeline,),
    )


def _stop_guard(guard: subprocess.Popen) -> None:
    if guard.poll() is None:
        guard.terminate()
        try:
            guard.wait(timeout=15)
        except subprocess.TimeoutExpired:
            guard.kill()
            guard.wait()


_LIFELINE: dict[int, tuple[int, int]] = {}
_LIFELINE_LOCK = threading.Lock()


def _lifeline() -> int:
    """Đầu đọc của một pipe chung cho cả tiến trình; đầu ghi không kế thừa, chỉ đóng khi tiến trình này chết."""
    with _LIFELINE_LOCK:
        pid = os.getpid()
        if pid not in _LIFELINE:
            _LIFELINE[pid] = os.pipe()
        return _LIFELINE[pid][0]


def _drop_lifeline_after_fork() -> None:
    global _LIFELINE_LOCK
    _LIFELINE_LOCK = threading.Lock()
    for fds in _LIFELINE.values():
        for fd in fds:
            try:
                os.close(fd)
            except OSError:
                pass
    _LIFELINE.clear()


os.register_at_fork(after_in_child=_drop_lifeline_after_fork)


class _PortTaken(Exception):
    pass


def _tail(path: Path, lines: int = 30) -> str:
    try:
        return "\n".join(path.read_text(errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


class VM:
    """VM đang chạy của một lần chạy. Chỉ lấy qua `with fdekit.vm(...) as m:`."""

    def __init__(self, run_id: str, run_dir: Path, ssh_port: int, ports: Mapping[int, int],
                 guard: subprocess.Popen) -> None:
        self.run_id = run_id
        self.name = PREFIX + run_id
        self.dir = run_dir
        self.key = run_dir / "id_ed25519"
        self.overlay = run_dir / "disk.qcow2"
        self.ssh_port = ssh_port
        self._ports = dict(ports)
        self._guard = guard
        self._started = False

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
        """`cmd` là một chuỗi shell chạy phía VM; phần nào không tin cậy phải `shlex.quote` trước."""
        result = subprocess.run([*self.ssh_command(user), cmd], capture_output=True, text=True, timeout=timeout,
                                stdin=subprocess.DEVNULL)
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        return result

    def _scp(self, source: str, target: str) -> None:
        result = subprocess.run(["scp", "-q", "-r", *self._options(), "-P", str(self.ssh_port), "--", source, target],
                                capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            raise RuntimeError(f"scp {source} → {target} lỗi ({result.returncode}): {result.stderr.strip()}")

    def put(self, local: Path, remote: str) -> None:
        self._scp(str(Path(local).resolve()), f"fde@127.0.0.1:{remote}")

    def get(self, remote: str, local: Path) -> None:
        self._scp(f"fde@127.0.0.1:{remote}", str(Path(local).resolve()))

    def port(self, guest_port: int) -> int:
        if guest_port not in self._ports:
            raise KeyError(f"Cổng {guest_port} của VM chưa được forward; thêm vào vm(..., forwards=({guest_port},))")
        return self._ports[guest_port]

    def _start(self, args: list[str]) -> None:
        (self.dir / "qemu.exit").unlink(missing_ok=True)
        part = self.dir / "qemu.start.tmp"
        part.write_text(json.dumps(args))
        os.replace(part, self.dir / "qemu.start")
        self._started = True

    def _running(self) -> bool:
        return self._started and self._guard.poll() is None and not (self.dir / "qemu.exit").exists()

    def _wait_exit(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while self._running() and time.monotonic() < deadline:
            time.sleep(0.2)
        return not self._running()

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
            except (OSError, ValueError):
                pass
            self._wait_exit(min(20, max(1, deadline - time.monotonic())))
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
            self._guard.send_signal(signal.SIGUSR1)
            if not self._wait_exit(15):
                for pid in _qemu_pids(self.run_id):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                self._wait_exit(10)
        self._started = False


_ACTIVE: set[str] = set()
_GUARDS: dict[str, subprocess.Popen] = {}


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


def _vm_defaults(profile: str | None, *, restrict: bool | None, sudo: bool | None) -> tuple[bool, bool]:
    spec = _profile(profile) if profile is not None else None
    if restrict is None:
        restrict = spec is not None and spec.egress != "open"
    if sudo is None:
        sudo = spec is not None and spec.sudo
    return restrict, sudo


def _new_run_dir(run_id: str) -> Path:
    run_dir = LAB / f"{PREFIX}{run_id}"
    if len(str(run_dir / "qmp.sock")) > 100:
        raise RuntimeError(f"Đường dẫn repo quá dài cho unix socket của QEMU ({run_dir}); clone repo vào thư mục ngắn hơn")
    run_dir.mkdir(parents=True, mode=0o700)
    return run_dir


@contextmanager
def vm(profile: str | None, *, memory_mb: int = 2048, cpus: int = 2, forwards: Sequence[int] = (),
       guestfwds: Mapping[str, int] | None = None, base: Path | None = None, restrict: bool | None = None,
       sudo: bool | None = None, cloud_config: Mapping | None = None, run_id: str | None = None) -> Iterator[VM]:
    """Boot một VM từ overlay qcow2 trên golden của `profile` (hoặc trên `base`), chờ SSH rồi trả `VM`; luôn dọn khi ra.

    `guestfwds` ánh xạ "ip:port" phía VM → cổng 127.0.0.1 phía host. `restrict`/`sudo` mặc định theo hồ sơ khách:
    egress `none`/`proxy` ⇒ `restrict=True` (không ra internet, không tới loopback host, trừ forward đã khai báo).
    `run_id` chỉ dùng khi thư mục lab của run id đó đã được tạo (customer_site dùng chung run id với container).
    """
    restrict, sudo = _vm_defaults(profile, restrict=restrict, sudo=sudo)
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
    owned = run_id is None
    if not owned and run_id not in _GUARDS:
        raise ValueError(f"run id {run_id!r} không có tiến trình canh; chỉ customer_site truyền run_id")
    run_id = run_id or uuid.uuid4().hex[:8]
    if owned:
        _ACTIVE.add(run_id)
    machine: VM | None = None
    guard: subprocess.Popen | None = None
    try:
        if owned:
            run_dir = _new_run_dir(run_id)
            guard = _spawn_guard(run_dir)
        else:
            run_dir, guard = LAB / f"{PREFIX}{run_id}", _GUARDS[run_id]
        key = generate_key(run_dir / "id_ed25519")
        seed = write_seed_iso(run_dir / "seed.iso", instance_id=f"{PREFIX}{run_id}",
                              public_key=key.with_name(key.name + ".pub").read_text().strip(), sudo=sudo,
                              cloud_config=cloud_config)
        subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", "-F", _image_format(base), "-b", str(base),
                        str(run_dir / "disk.qcow2")], check=True, capture_output=True, text=True)
        relay = _write_relay(run_dir) if guestfwds else None
        for attempt in range(3):
            ports = {int(guest): testkit.free_port() for guest in forwards}
            machine = VM(run_id, run_dir, testkit.free_port(), ports, guard)
            netdev = _netdev(ssh_port=machine.ssh_port, forwards=ports, guestfwds=guestfwds or {}, restrict=restrict,
                             relay=relay)
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
        if owned:
            try:
                if guard is not None:
                    _stop_guard(guard)
                clean(run_id)
            finally:
                _ACTIVE.discard(run_id)


@dataclass
class Site:
    """Một "khách hàng" đang chạy: VM theo hồ sơ cùng dịch vụ phía host (proxy, registry) của đúng run id này."""

    vm: VM
    profile: Profile
    proxy_ca: Path | None = None
    registry: str | None = None
    registry_host: str | None = None


class _SiteLab(testkit.DockerLab):
    def __init__(self, run_id: str) -> None:
        super().__init__()
        self.id = run_id
        self.network = f"{PREFIX}{run_id}"


def _require_site_images(spec: Profile) -> None:
    if not testkit.docker_ready():
        pytest.skip("Hồ sơ khách này cần Docker phía host (daemon đang chạy) cho proxy/registry (testkit.DockerLab)")
    for service in spec.services:
        testkit.Exercise.require_image(SITE_IMAGES[service])


def _start_proxy(lab: _SiteLab, run_dir: Path, *, tls_inspection: bool) -> Path:
    command = ["mitmdump", "--listen-host", "0.0.0.0", "--listen-port", "8080"]
    if not tls_inspection:
        command += ["--ignore-hosts", ".*"]
    lab.start("proxy", MITMPROXY_IMAGE, *command, ports=(8080,), env={"PYTHONUNBUFFERED": "1"}, memory="512m")
    lab.wait_http("proxy", f"http://127.0.0.1:{lab.port('proxy', 8080)}/", timeout=60)
    deadline = time.monotonic() + 30
    while True:
        cert = lab.exec("proxy", "cat", "/home/mitmproxy/.mitmproxy/mitmproxy-ca-cert.pem")
        if cert.returncode == 0 and "END CERTIFICATE" in cert.stdout:
            break
        if time.monotonic() > deadline:
            pytest.fail(f"Không lấy được CA của mitmproxy: {cert.stderr.strip()}")
        time.sleep(0.3)
    path = run_dir / "proxy-ca.pem"
    path.write_text(cert.stdout)
    return path


def _start_registry(lab: _SiteLab) -> int:
    lab.start("registry", REGISTRY_IMAGE, ports=(5000,))
    port = lab.port("registry", 5000)
    lab.wait_http("registry", f"http://127.0.0.1:{port}/v2/", timeout=60)
    return port


@contextmanager
def customer_site(profile: str, *, memory_mb: int = SITE_MEMORY_MB, forwards: Sequence[int] = ()) -> Iterator[Site]:
    """Dựng "khách hàng" theo hồ sơ: container proxy (mitmproxy, TLS inspection, CA riêng mỗi lần chạy) và/hoặc
    registry nội bộ phía host (chỉ 127.0.0.1, tên `fde-ex-<run_id>-*`), rồi VM với egress theo hồ sơ. Trong VM:
    proxy ở `10.0.2.100:3128`, registry ở `10.0.2.101:5000`. Một tiến trình canh cho cả run id: mọi thứ bị dọn khi ra,
    kể cả khi pytest bị SIGKILL."""
    spec = _profile(profile)
    require_golden(profile)
    _require_ssh_tools()
    _require_memory(memory_mb)
    if spec.services:
        _require_site_images(spec)
    run_id = uuid.uuid4().hex[:8]
    _ACTIVE.add(run_id)
    try:
        run_dir = _new_run_dir(run_id)
        _GUARDS[run_id] = _spawn_guard(run_dir)
        if spec.services:
            (run_dir / "containers").touch()
        with _SiteLab(run_id) as lab:
            guestfwds: dict[str, int] = {}
            proxy_ca = registry = registry_host = None
            if "proxy" in spec.services:
                proxy_ca = _start_proxy(lab, run_dir, tls_inspection=spec.tls_inspection)
                guestfwds[PROXY_ADDR] = lab.port("proxy", 8080)
            if "registry" in spec.services:
                host_port = _start_registry(lab)
                guestfwds[REGISTRY_ADDR] = host_port
                registry, registry_host = REGISTRY_ADDR, f"127.0.0.1:{host_port}"
            with vm(profile, memory_mb=memory_mb, cpus=SITE_CPUS, forwards=forwards, guestfwds=guestfwds,
                    run_id=run_id) as machine:
                yield Site(machine, spec, proxy_ca, registry, registry_host)
    finally:
        try:
            guard = _GUARDS.pop(run_id, None)
            if guard is not None:
                _stop_guard(guard)
            clean(run_id)
        finally:
            _ACTIVE.discard(run_id)


_RELAY_NAME = "guestfwd-relay.py"


def _processes(needle: str) -> list[tuple[int, str, str]]:
    """(pid, loại, dòng lệnh) của tiến trình thuộc `needle`; loại là "qemu", "guard" hoặc "relay"."""
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
            found.append((int(entry.name), "qemu", " ".join(args)[:160]))
        elif _GUARD in args:
            found.append((int(entry.name), "guard", " ".join(args[args.index(_GUARD):])[:160]))
        elif any(a.endswith(_RELAY_NAME) and needle in a for a in args):
            found.append((int(entry.name), "relay", " ".join(args)[:160]))
    return found


def _qemu_pids(run_id: str) -> list[int]:
    return [pid for pid, kind, _ in _processes(f"{PREFIX}{run_id}") if kind == "qemu"]


def _docker_names(kind: list[str], fmt: str, needle: str) -> list[str]:
    if not shutil.which("docker"):
        return []
    try:
        result = subprocess.run(["docker", *kind, "--filter", f"name={needle}", "--format", fmt],
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return []
    return [name for name in result.stdout.split() if name.startswith(needle)] if result.returncode == 0 else []


def _containers(needle: str) -> list[str]:
    return _docker_names(["ps", "-a"], "{{.Names}}", needle)


def _networks(needle: str) -> list[str]:
    return _docker_names(["network", "ls"], "{{.Name}}", needle)


def leftovers(run_id: str | None = None) -> list[str]:
    """Tiến trình QEMU, thư mục lab (overlay, seed, key) và container còn sót. `run_id=None` chỉ để báo cáo."""
    needle = f"{PREFIX}{run_id}" if run_id else PREFIX
    found = [f"process {pid}: {line}" for pid, _, line in _processes(needle)]
    if LAB.is_dir():
        found += sorted(str(path) for path in LAB.iterdir() if path.name.startswith(needle))
    found += [f"container {name}" for name in _containers(needle)]
    found += [f"network {name}" for name in _networks(needle)]
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
    for command, names in ((["rm", "-f"], _containers(needle)), (["network", "rm"], _networks(needle))):
        if names:
            try:
                subprocess.run(["docker", *command, *names], capture_output=True, timeout=60)
            except (OSError, subprocess.SubprocessError) as error:
                print(f"Không xoá được {names}: {error}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m fdekit", description="VM khách hàng cho track FDE")
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="dựng golden image của một hồ sơ khách")
    prep.add_argument("profile")
    prep.add_argument("--force", action="store_true")
    commands.add_parser("leftovers", help="liệt kê tiến trình QEMU, overlay, container/network fde-ex-* còn sót")
    cleaner = commands.add_parser("clean", help="dọn mọi thứ của một run id")
    cleaner.add_argument("run_id")
    args = parser.parse_args(argv)
    if args.command == "prepare":
        started = time.monotonic()
        try:
            golden = prepare(args.profile, force=args.force)
        except UnknownProfile as error:
            print(error.args[0], file=sys.stderr)
            return 2
        except pytest.skip.Exception as error:
            print(error.msg, file=sys.stderr)
            return 2
        except (RuntimeError, subprocess.SubprocessError, OSError) as error:
            print(error, file=sys.stderr)
            return 1
        size = golden.stat().st_size / 1024 ** 3
        print(f"{golden} ({size:.2f} GiB, {time.monotonic() - started:.0f} s)")
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
