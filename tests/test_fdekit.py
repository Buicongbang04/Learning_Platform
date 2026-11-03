import hashlib
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pycdlib
import pytest
import requests
import yaml

import fdekit


def test_images_pinned():
    assert set(fdekit.IMAGES) == {"ubuntu-22.04", "ubuntu-20.04", "rocky-8", "debian-12"}
    for image in fdekit.IMAGES.values():
        assert "current" not in image.url and "latest" not in image.url
        assert image.url.startswith("https://")
        assert len(image.sha256) == 64
        int(image.sha256, 16)


def test_require_kvm_skips(monkeypatch):
    monkeypatch.setattr(fdekit.os, "access", lambda *args, **kwargs: False)
    with pytest.raises(pytest.skip.Exception) as info:
        fdekit.require_kvm()
    assert "Cần /dev/kvm đọc/ghi được và qemu-system-x86_64" in str(info.value)


def test_require_kvm_skips_without_qemu(monkeypatch):
    monkeypatch.setattr(fdekit.os, "access", lambda *args, **kwargs: True)
    monkeypatch.setattr(fdekit.shutil, "which", lambda name: None)
    with pytest.raises(pytest.skip.Exception):
        fdekit.require_kvm()


def test_golden_missing_skips_with_command(tmp_path, monkeypatch):
    monkeypatch.setattr(fdekit, "CACHE", tmp_path)
    monkeypatch.setattr(fdekit, "require_kvm", lambda: None)
    assert fdekit.golden_path("lab-open").is_relative_to(tmp_path)
    with pytest.raises(pytest.skip.Exception) as info:
        fdekit.require_golden("lab-open")
    assert "uv run python -m fdekit prepare lab-open" in str(info.value)


def test_require_golden_returns_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(fdekit, "CACHE", tmp_path)
    monkeypatch.setattr(fdekit, "require_kvm", lambda: None)
    golden = fdekit.golden_path("lab-open")
    golden.parent.mkdir(parents=True, exist_ok=True)
    golden.write_bytes(b"qcow")
    assert fdekit.require_golden("lab-open") == golden


def test_fetch_image_verifies_and_redownloads(tmp_path, monkeypatch):
    payload = b"fake cloud image"
    image = fdekit.CloudImage(
        url="https://example.invalid/releases/20260101/fake.img",
        sha256=hashlib.sha256(payload).hexdigest(),
        os_id="ubuntu",
        os_version="22.04",
    )
    monkeypatch.setattr(fdekit, "CACHE", tmp_path)
    monkeypatch.setitem(fdekit.IMAGES, "fake", image)
    calls = []

    def fake_download(url, dest):
        calls.append(url)
        dest.write_bytes(payload)

    monkeypatch.setattr(fdekit, "_download", fake_download)
    path = fdekit.fetch_image("fake")
    assert path.read_bytes() == payload and calls == [image.url]
    fdekit.fetch_image("fake")
    assert len(calls) == 1
    path.write_bytes(b"corrupted")
    fdekit.fetch_image("fake")
    assert len(calls) == 2 and path.read_bytes() == payload


def test_ubuntu_helper_skips_when_offline(monkeypatch):
    monkeypatch.setattr(fdekit, "require_kvm", lambda: None)

    def offline(name):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(fdekit, "fetch_image", offline)
    with pytest.raises(pytest.skip.Exception) as info:
        _ubuntu()
    assert "fdekit.fetch_image('ubuntu-22.04')" in str(info.value)


def test_ubuntu_helper_skips_on_sha_mismatch(monkeypatch):
    monkeypatch.setattr(fdekit, "require_kvm", lambda: None)

    def tampered(name):
        raise RuntimeError("sha256 của x không khớp")

    monkeypatch.setattr(fdekit, "fetch_image", tampered)
    with pytest.raises(pytest.skip.Exception) as info:
        _ubuntu()
    assert "sha256 không khớp" in str(info.value) and "fdekit.fetch_image('ubuntu-22.04')" in str(info.value)


def test_seed_rejects_reserved_cloud_config(tmp_path):
    for key in ("users", "ssh_pwauth", "disable_root"):
        with pytest.raises(ValueError, match=key):
            fdekit.write_seed_iso(tmp_path / "seed.iso", instance_id="fde-ex-deadbeef", public_key="ssh-ed25519 AAAA x",
                                  cloud_config={key: []})
    fdekit.write_seed_iso(tmp_path / "seed.iso", instance_id="fde-ex-deadbeef", public_key="ssh-ed25519 AAAA x",
                          cloud_config={"runcmd": ["true"]})


def test_forked_child_drops_lifeline():
    read_fd = fdekit._lifeline()
    write_fd = fdekit._LIFELINE[os.getpid()][1]
    pid = os.fork()
    if pid == 0:
        closed = 0
        for fd in (read_fd, write_fd):
            try:
                os.fstat(fd)
            except OSError:
                closed += 1
        os._exit(0 if closed == 2 and not fdekit._LIFELINE else 1)
    _, status = os.waitpid(pid, 0)
    assert os.waitstatus_to_exitcode(status) == 0
    os.fstat(write_fd)


def test_fetch_image_rejects_bad_download(tmp_path, monkeypatch):
    image = fdekit.CloudImage(url="https://example.invalid/r/1/x.img", sha256="0" * 64, os_id="x", os_version="1")
    monkeypatch.setattr(fdekit, "CACHE", tmp_path)
    monkeypatch.setitem(fdekit.IMAGES, "bad", image)
    monkeypatch.setattr(fdekit, "_download", lambda url, dest: dest.write_bytes(b"wrong"))
    with pytest.raises(RuntimeError, match="sha256"):
        fdekit.fetch_image("bad")
    assert not any(tmp_path.glob("x.img*"))


def test_seed_iso_has_cidata_label(tmp_path):
    key = fdekit.generate_key(tmp_path / "id_ed25519")
    public = key.with_suffix(".pub").read_text().strip()
    private = key.read_text()
    iso_path = fdekit.write_seed_iso(tmp_path / "seed.iso", instance_id="fde-ex-deadbeef", public_key=public)
    iso = pycdlib.PyCdlib()
    iso.open(str(iso_path))
    try:
        assert iso.pvd.volume_identifier.decode().strip() == "cidata"
        files = {}
        for name in ("user-data", "meta-data"):
            buffer = BytesIO()
            iso.get_file_from_iso_fp(buffer, joliet_path=f"/{name}")
            files[name] = buffer.getvalue().decode()
    finally:
        iso.close()
    assert files["user-data"].startswith("#cloud-config")
    assert public in files["user-data"]
    assert "PRIVATE KEY" not in files["user-data"] + files["meta-data"]
    assert private.strip().splitlines()[1] not in files["user-data"]
    assert "fde-ex-deadbeef" in files["meta-data"]


def test_netdev_args(tmp_path):
    relay = tmp_path / "relay.py"
    arg = fdekit._netdev(ssh_port=2222, forwards={8000: 31000}, guestfwds={"10.0.2.100:3128": 41000}, restrict=True,
                         relay=relay)
    assert arg.startswith("user,id=n0,restrict=on,")
    assert "hostfwd=tcp:127.0.0.1:2222-:22" in arg
    assert "hostfwd=tcp:127.0.0.1:31000-:8000" in arg
    command = f"{shlex.quote(sys.executable)} -I {shlex.quote(str(relay))} 127.0.0.1 41000"
    assert f"guestfwd=tcp:10.0.2.100:3128-cmd:{command.replace(',', ',,')}" in arg
    assert "restrict=off" in fdekit._netdev(ssh_port=2222, forwards={}, guestfwds={}, restrict=False, relay=relay)


def test_relay_bridges_stdio_to_host_port(tmp_path):
    relay = fdekit._write_relay(tmp_path)
    with socket.create_server(("127.0.0.1", 0)) as server:
        port = server.getsockname()[1]
        guest, qemu_side = socket.socketpair()
        child = subprocess.Popen([sys.executable, "-I", str(relay), "127.0.0.1", str(port)], stdin=qemu_side,
                                 stdout=qemu_side, stderr=subprocess.DEVNULL)
        qemu_side.close()
        try:
            conn, _ = server.accept()
            with conn:
                guest.sendall(b"ping")
                assert conn.recv(4) == b"ping"
                conn.sendall(b"pong")
                assert guest.recv(4) == b"pong"
            assert guest.recv(1) == b""
            child.wait(timeout=5)
        finally:
            guest.close()
            if child.poll() is None:
                child.kill()


def test_relay_half_close(tmp_path):
    relay = fdekit._write_relay(tmp_path)
    with socket.create_server(("127.0.0.1", 0)) as server:
        port = server.getsockname()[1]
        guest, qemu_side = socket.socketpair()
        child = subprocess.Popen([sys.executable, "-I", str(relay), "127.0.0.1", str(port)], stdin=qemu_side,
                                 stdout=qemu_side, stderr=subprocess.DEVNULL)
        qemu_side.close()
        try:
            conn, _ = server.accept()
            with conn:
                guest.sendall(b"request")
                guest.shutdown(socket.SHUT_WR)
                received = b""
                while chunk := conn.recv(64):
                    received += chunk
                assert received == b"request"
                conn.sendall(b"response")
            reply = b""
            while chunk := guest.recv(64):
                reply += chunk
            assert reply == b"response"
            child.wait(timeout=5)
        finally:
            guest.close()
            if child.poll() is None:
                child.kill()


def _profile_yaml(tmp_path, **overrides):
    data = {"image": "ubuntu-22.04", "disk_gb": 20, "sudo": True, "egress": "open", "tls_inspection": False,
            "selinux": "n/a", "runtime": "docker", "services": [],
            "facts": {"kernel_major": "5.15", "glibc": "2.35", "disk_free_gb_max": 18, "gpu": None}}
    facts = overrides.pop("facts", {})
    data.update(overrides)
    data["facts"] = {**data["facts"], **facts}
    path = tmp_path / "x.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


def test_profile_loader_validates(tmp_path):
    assert fdekit._load_profile(_profile_yaml(tmp_path)).facts["glibc"] == "2.35"
    for overrides, message in (
        ({"facts": {"glibc": 2.3}}, "glibc"),
        ({"facts": {"kernel_major": 5.10}}, "kernel_major"),
        ({"tls_inspection": True}, "tls_inspection"),
        ({"facts": {"disk_free_gb_max": 20}}, "disk_free_gb_max"),
        ({"egress": "proxy"}, "services"),
        ({"image": "windows-11"}, "image"),
    ):
        with pytest.raises(ValueError, match=message):
            fdekit._load_profile(_profile_yaml(tmp_path, **overrides))


def test_vm_rejects_unknown_profile_and_foreign_run_id():
    with pytest.raises(KeyError, match="no-such-customer"):
        fdekit._vm_defaults("no-such-customer", restrict=None, sudo=None)
    with pytest.raises(ValueError, match="run id"):
        with fdekit.vm(None, base=fdekit.__file__, run_id="deadbeef"):
            pass


def test_guard_halt_cancels_pending_qemu_start(tmp_path):
    run_dir = tmp_path / "fde-ex-aaaaaaaa"
    run_dir.mkdir()
    marker = tmp_path / "launched"
    guard = fdekit._spawn_guard(run_dir)
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            caught = int(next(line for line in open(f"/proc/{guard.pid}/status") if line.startswith("SigCgt")).split()[1], 16)
            if caught & (1 << (signal.SIGUSR1 - 1)):
                break
            time.sleep(0.05)
        os.kill(guard.pid, signal.SIGSTOP)
        (run_dir / "qemu.start").write_text(f'["touch", "{marker}"]')
        os.kill(guard.pid, signal.SIGUSR1)
        os.kill(guard.pid, signal.SIGCONT)
        time.sleep(1.5)
        assert not marker.exists()
        assert not (run_dir / "qemu.start").exists()
    finally:
        fdekit._stop_guard(guard)


def test_relay_matcher_only_matches_this_runs_relay(tmp_path):
    namespace = {"os": os}
    exec(fdekit._RELAY_MATCH, namespace)
    mine, other = tmp_path / "fde-ex-aaaaaaaa", tmp_path / "fde-ex-bbbbbbbb"
    procs = [subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", str(d / fdekit._RELAY_NAME)])
             for d in (mine, other)]
    try:
        time.sleep(0.5)
        assert namespace["relay_pids"](str(mine / fdekit._RELAY_NAME)) == [procs[0].pid]
    finally:
        for proc in procs:
            proc.kill()
            proc.wait()


def test_vm_checks_run_id_before_host_prerequisites(monkeypatch):
    monkeypatch.setattr(fdekit, "require_kvm", lambda: pytest.fail("require_kvm được gọi trước kiểm tra run id"))
    with pytest.raises(ValueError, match="run id"):
        with fdekit.vm("lab-open", run_id="deadbeef"):
            pass


SURVEY_KEYS = {"os_id", "os_version", "kernel_major", "glibc", "cpus", "mem_mb", "disk_free_gb_max", "gpu", "proxy_url",
               "sudo", "selinux", "runtime", "egress"}


def test_profiles_load():
    assert set(fdekit.PROFILES) >= {"lab-open", "hospital", "bank", "lawfirm-staging"}
    for name, profile in fdekit.PROFILES.items():
        assert profile.name == name
        assert profile.image in fdekit.IMAGES
        assert profile.egress in ("open", "proxy", "none")
        assert profile.runtime in ("docker", "podman", "k3s", "none")
        assert set(profile.services) <= {"proxy", "registry"}
        assert ("proxy" in profile.services) == (profile.egress == "proxy")
        assert profile.tls_inspection <= (profile.egress == "proxy")
    hospital, bank = fdekit.PROFILES["hospital"], fdekit.PROFILES["bank"]
    assert (hospital.image, hospital.disk_gb, hospital.egress, hospital.tls_inspection) == ("ubuntu-20.04", 8, "proxy", True)
    assert (bank.image, bank.sudo, bank.egress, bank.selinux, bank.runtime) == ("rocky-8", False, "none", "enforcing", "podman")
    assert fdekit.PROFILES["lawfirm-staging"].services == ["registry"]
    assert fdekit.PROFILES["lab-open"].egress == "open"


def test_facts_cover_survey_keys():
    for profile in fdekit.PROFILES.values():
        assert set(profile.facts) >= SURVEY_KEYS, profile.name
        facts = profile.facts
        assert facts["os_id"] == fdekit.IMAGES[profile.image].os_id
        assert facts["os_version"] == fdekit.IMAGES[profile.image].os_version
        assert (facts["sudo"], facts["selinux"], facts["runtime"], facts["egress"]) == (
            profile.sudo, profile.selinux, profile.runtime, profile.egress)
        assert (facts["cpus"], facts["mem_mb"]) == (fdekit.SITE_CPUS, fdekit.SITE_MEMORY_MB)
        assert facts["disk_free_gb_max"] < profile.disk_gb
        assert facts["proxy_url"] == ("http://10.0.2.100:3128" if profile.egress == "proxy" else None)


def test_profile_network_defaults():
    assert fdekit._vm_defaults("lab-open", restrict=None, sudo=None) == (False, True)
    assert fdekit._vm_defaults("hospital", restrict=None, sudo=None) == (True, True)
    assert fdekit._vm_defaults("bank", restrict=None, sudo=None) == (True, False)
    assert fdekit._vm_defaults("lawfirm-staging", restrict=None, sudo=None) == (True, True)
    assert fdekit._vm_defaults(None, restrict=None, sudo=None) == (False, False)
    assert fdekit._vm_defaults("bank", restrict=False, sudo=True) == (False, True)


def test_site_images_pinned():
    for image in (fdekit.MITMPROXY_IMAGE, fdekit.REGISTRY_IMAGE):
        name, digest = image.split("@sha256:")
        assert ":" in name and not name.endswith((":latest", ":2", ":12"))
        assert len(digest) == 64
        int(digest, 16)


def test_prepare_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(fdekit, "CACHE", tmp_path)
    golden = fdekit.golden_path("lab-open")
    golden.parent.mkdir(parents=True)
    golden.write_bytes(b"qcow")

    def boom(*args, **kwargs):
        raise AssertionError("không được boot lại khi golden đã có")

    monkeypatch.setattr(fdekit, "vm", boom)
    monkeypatch.setattr(fdekit, "fetch_image", boom)
    assert fdekit.prepare("lab-open") == golden


def test_prepare_scripts_exist():
    for profile in fdekit.PROFILES.values():
        script = fdekit.prepare_script(profile.name)
        assert script.is_file() and script.read_text().startswith("#!/bin/bash")


def test_clean_rejects_bad_run_id():
    for bad in ("", "*", "../x", "fde-ex-", "abc"):
        with pytest.raises(ValueError):
            fdekit.clean(bad)


def test_leftovers_reports_run_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(fdekit, "LAB", tmp_path)
    (tmp_path / "fde-ex-0badc0de").mkdir()
    (tmp_path / "fde-ex-12345678").mkdir()
    monkeypatch.setattr(fdekit, "_containers", lambda needle: [])
    monkeypatch.setattr(fdekit, "_networks", lambda needle: [])
    assert fdekit.leftovers("0badc0de") == [str(tmp_path / "fde-ex-0badc0de")]
    assert len(fdekit.leftovers()) == 2
    fdekit.clean("0badc0de")
    assert fdekit.leftovers("0badc0de") == []
    assert (tmp_path / "fde-ex-12345678").exists()


def test_cli_prepare_unknown_profile(capsys):
    code = fdekit.main(["prepare", "no-such-customer"])
    assert code != 0
    err = capsys.readouterr().err
    assert "no-such-customer" in err and "lab-open" in err


def test_capstone_dir_skips_when_unset(monkeypatch):
    monkeypatch.delenv("FDE_CAPSTONE_DIR", raising=False)
    monkeypatch.delenv("SOLUTION", raising=False)
    with pytest.raises(pytest.skip.Exception) as info:
        fdekit.capstone_dir()
    assert "Đặt FDE_CAPSTONE_DIR=<đường dẫn repo capstone của bạn> trong setup/.env" in str(info.value)


def test_capstone_dir_from_env(tmp_path, monkeypatch):
    monkeypatch.delenv("SOLUTION", raising=False)
    monkeypatch.setenv("FDE_CAPSTONE_DIR", str(tmp_path))
    assert fdekit.capstone_dir() == tmp_path


def test_capstone_dir_solution(monkeypatch):
    monkeypatch.setenv("SOLUTION", "1")
    monkeypatch.delenv("FDE_CAPSTONE_DIR", raising=False)
    path = fdekit.capstone_dir()
    assert path.as_posix().endswith("capstone/solutions/project")
    assert path.is_relative_to(fdekit.ROOT / "tracks" / "fde")


FETCH = "uv run python -c \"import fdekit; fdekit.fetch_image('ubuntu-22.04')\""


def _ubuntu():
    fdekit.require_kvm()
    try:
        return fdekit.fetch_image("ubuntu-22.04")
    except (OSError, requests.RequestException) as error:
        pytest.skip(f"Chưa có cloud image ubuntu-22.04 và tải không được ({error}). Tải trước (~730 MB): {FETCH}")
    except RuntimeError as error:
        pytest.skip(f"Tải cloud image ubuntu-22.04 nhưng sha256 không khớp (tệp hỏng hoặc mạng chặn/đổi nội dung): {error}. "
                    f"Kiểm tra mạng rồi tải lại: {FETCH}")


def test_vm_boots_and_ssh():
    base = _ubuntu()
    with fdekit.vm(None, base=base, memory_mb=1024, forwards=(8000,)) as m:
        assert m.ssh("uname -s").stdout.strip() == "Linux"
        assert m.ssh("id -un").stdout.strip() == "fde"
        assert m.port(8000) > 0
        command = m.ssh_command()
        assert command[0] == "ssh" and command[-1].endswith("@127.0.0.1")
        run_id = m.run_id
        assert fdekit.leftovers(run_id)
    assert fdekit.leftovers(run_id) == []


def test_vm_put_get_from_worker_thread(tmp_path):
    base = _ubuntu()
    source = tmp_path / "hello.txt"
    source.write_text("xin chào\n")
    manager = fdekit.vm(None, base=base, memory_mb=1024)
    with ThreadPoolExecutor(max_workers=1) as pool:
        m = pool.submit(manager.__enter__).result()
    try:
        time.sleep(3)
        assert fdekit._qemu_pids(m.run_id)
        assert m.dir.is_dir()
        m.put(source, "/home/fde/hello.txt")
        assert m.ssh("cat /home/fde/hello.txt").stdout == "xin chào\n"
        m.get("/etc/hostname", tmp_path / "hostname")
    finally:
        manager.__exit__(None, None, None)
    assert (tmp_path / "hostname").read_text().strip()
    assert fdekit.leftovers(m.run_id) == []


def test_vm_cleanup_on_error():
    base = _ubuntu()
    run_id = None
    with pytest.raises(RuntimeError, match="boom"):
        with fdekit.vm(None, base=base, memory_mb=1024) as m:
            run_id = m.run_id
            raise RuntimeError("boom")
    assert run_id and fdekit.leftovers(run_id) == []


CHILD = """
import sys, time
import fdekit
with fdekit.vm(None, base=fdekit.fetch_image("ubuntu-22.04"), memory_mb=1024) as m:
    print(m.run_id, flush=True)
    time.sleep(600)
"""


def test_qemu_dies_with_parent(tmp_path):
    _ubuntu()
    run_id = ""
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD], cwd=fdekit.ROOT, stdout=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": str(fdekit.ROOT)},
    )
    try:
        run_id = child.stdout.readline().strip()
        assert len(run_id) == 8, "tiến trình con không mở được VM"
        assert fdekit._qemu_pids(run_id)
        os.kill(child.pid, signal.SIGKILL)
        child.wait(timeout=10)
        deadline = time.monotonic() + 10
        while fdekit._qemu_pids(run_id) and time.monotonic() < deadline:
            time.sleep(0.2)
        assert fdekit._qemu_pids(run_id) == []
        deadline = time.monotonic() + 10
        while fdekit.leftovers(run_id) and time.monotonic() < deadline:
            time.sleep(0.2)
        assert fdekit.leftovers(run_id) == []
    finally:
        if child.poll() is None:
            child.kill()
        if len(run_id) == 8:
            fdekit.clean(run_id)


FORK_CHILD = """
import os, time
import fdekit
with fdekit.vm(None, base=fdekit.fetch_image("ubuntu-22.04"), memory_mb=1024) as m:
    worker = os.fork()
    if worker == 0:
        time.sleep(600)
        os._exit(0)
    print(m.run_id, worker, flush=True)
    time.sleep(600)
"""


def test_qemu_dies_with_parent_despite_forked_worker():
    _ubuntu()
    run_id, worker = "", 0
    child = subprocess.Popen(
        [sys.executable, "-c", FORK_CHILD], cwd=fdekit.ROOT, stdout=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": str(fdekit.ROOT)},
    )
    try:
        run_id, worker = child.stdout.readline().split()
        worker = int(worker)
        assert fdekit._qemu_pids(run_id)
        os.kill(child.pid, signal.SIGKILL)
        child.wait(timeout=10)
        deadline = time.monotonic() + 10
        while fdekit._qemu_pids(run_id) and time.monotonic() < deadline:
            time.sleep(0.2)
        assert fdekit._qemu_pids(run_id) == []
        os.kill(worker, 0)
    finally:
        if child.poll() is None:
            child.kill()
        if worker:
            try:
                os.kill(worker, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if len(run_id) == 8:
            fdekit.clean(run_id)


def test_snapshot_roundtrip(tmp_path):
    base = _ubuntu()
    snap = tmp_path / "snap.qcow2"
    with fdekit.vm(None, base=base, memory_mb=1024) as m:
        m.ssh("echo milestone-1 > /home/fde/state.txt", check=True)
        m.snapshot(snap)
    info = subprocess.run(["qemu-img", "info", "--output=json", str(snap)], capture_output=True, text=True, check=True)
    assert '"backing-filename"' not in info.stdout
    with fdekit.vm(None, base=snap, memory_mb=1024) as m:
        assert m.ssh("cat /home/fde/state.txt").stdout.strip() == "milestone-1"


def _fails(m, cmd):
    result = m.ssh(cmd, timeout=90)
    assert result.returncode != 0, f"{cmd} phải thất bại nhưng chạy được:\n{result.stdout}"
    return result


def test_egress_none_blocks_internet_and_dns():
    with fdekit.customer_site("lawfirm-staging") as s:
        _fails(s.vm, "curl -sS --max-time 10 https://example.com")
        _fails(s.vm, "curl -sS --max-time 10 http://93.184.215.14/")
        _fails(s.vm, "getent hosts example.com")
        host_port = s.registry_host.rsplit(":", 1)[1]
        _fails(s.vm, f"curl -sS --max-time 5 http://10.0.2.2:{host_port}/v2/")
        _fails(s.vm, "curl -sS --max-time 5 http://10.0.2.2:22/")


def test_proxy_profile_only_reaches_proxy():
    with fdekit.customer_site("hospital") as s:
        _fails(s.vm, "curl -sS --noproxy '*' --max-time 10 https://pypi.org")
        _fails(s.vm, "getent hosts pypi.org")
        untrusted = _fails(s.vm, "curl -sS --max-time 30 -x http://10.0.2.100:3128 https://pypi.org -o /dev/null")
        assert untrusted.returncode == 60, untrusted.stderr
        assert s.proxy_ca is not None and "BEGIN CERTIFICATE" in s.proxy_ca.read_text()
        s.vm.put(s.proxy_ca, "/tmp/proxy-ca.pem")
        trusted = s.vm.ssh("curl -sS --max-time 30 -x http://10.0.2.100:3128 --cacert /tmp/proxy-ca.pem "
                           "-o /dev/null -w '%{http_code}' https://pypi.org/simple/pip/", timeout=90)
        assert trusted.stdout.strip() == "200", trusted.stderr
        system_store = s.vm.ssh("curl -sS --max-time 30 -o /dev/null https://pypi.org", timeout=90)
        assert system_store.returncode == 60, "CA của proxy không được trust sẵn trong VM"


def test_bank_no_sudo_selinux():
    with fdekit.customer_site("bank") as s:
        _fails(s.vm, "sudo -n true")
        assert s.vm.ssh("getenforce").stdout.strip() == "Enforcing"
        info = s.vm.ssh("podman info --format '{{.Host.Security.Rootless}}'", timeout=120)
        assert info.returncode == 0, info.stderr
        assert info.stdout.strip() == "true"
        _fails(s.vm, "curl -sS --max-time 10 https://example.com")
        assert s.proxy_ca is None and s.registry is None


def test_registry_reachable_from_vm():
    with fdekit.customer_site("lawfirm-staging") as s:
        assert s.registry == "10.0.2.101:5000"
        assert requests.get(f"http://{s.registry_host}/v2/", timeout=10).status_code == 200
        out = s.vm.ssh("curl -sS --max-time 10 -o /dev/null -w '%{http_code}' http://10.0.2.101:5000/v2/")
        assert out.stdout.strip() == "200", out.stderr
        again = s.vm.ssh("curl -sS --max-time 10 http://10.0.2.101:5000/v2/_catalog")
        assert '"repositories"' in again.stdout, again.stderr


FACT_PROBE = r"""
. /etc/os-release
echo "os_id=$ID"
echo "os_version=$VERSION_ID"
echo "kernel_major=$(uname -r | cut -d. -f1-2)"
echo "glibc=$(getconf GNU_LIBC_VERSION | awk '{print $2}')"
echo "cpus=$(nproc)"
echo "mem_kb=$(awk '/^MemTotal/ {print $2}' /proc/meminfo)"
echo "disk_avail_kb=$(df -P -k / | awk 'NR==2 {print $4}')"
echo "sudo=$(sudo -n true 2>/dev/null && echo yes || echo no)"
echo "selinux=$(command -v getenforce >/dev/null && getenforce | tr A-Z a-z || echo n/a)"
echo "docker=$(command -v docker >/dev/null && echo yes || echo no)"
echo "podman=$(command -v podman >/dev/null && echo yes || echo no)"
echo "gpu=$(ls /dev/nvidia0 2>/dev/null || echo none)"
echo "proxy=$(grep -h '^https_proxy=' /etc/environment 2>/dev/null | cut -d= -f2 | tr -d '\"')"
"""


@pytest.mark.parametrize("name", ["lab-open", "hospital", "bank", "lawfirm-staging"])
def test_facts_match_vm(name):
    profile = fdekit.PROFILES[name]
    facts = profile.facts
    with fdekit.customer_site(name) as s:
        result = s.vm.ssh(FACT_PROBE, timeout=60)
    assert result.returncode == 0, result.stderr
    seen = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    assert seen["os_id"] == facts["os_id"]
    assert seen["os_version"] == facts["os_version"]
    assert seen["kernel_major"] == facts["kernel_major"]
    assert seen["glibc"] == facts["glibc"]
    assert int(seen["cpus"]) == facts["cpus"]
    assert 0.8 * facts["mem_mb"] <= int(seen["mem_kb"]) / 1024 <= facts["mem_mb"]
    avail_gb = int(seen["disk_avail_kb"]) / 1024 / 1024
    assert facts["disk_free_gb_max"] - 2 <= avail_gb <= facts["disk_free_gb_max"], avail_gb
    assert (seen["sudo"] == "yes") == facts["sudo"]
    assert seen["selinux"] == facts["selinux"]
    assert seen[facts["runtime"]] == "yes"
    assert seen["gpu"] == "none" and facts["gpu"] is None
    assert (seen["proxy"] or None) == facts["proxy_url"]


SITE_CHILD = """
import time
import fdekit
with fdekit.customer_site("hospital") as s:
    print(s.vm.run_id, flush=True)
    time.sleep(600)
"""


def test_site_containers_die_with_parent():
    fdekit.require_golden("hospital")
    run_id = ""
    child = subprocess.Popen(
        [sys.executable, "-c", SITE_CHILD], cwd=fdekit.ROOT, stdout=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": str(fdekit.ROOT)},
    )
    try:
        run_id = child.stdout.readline().strip()
        assert len(run_id) == 8, "tiến trình con không mở được customer_site"
        assert fdekit._qemu_pids(run_id)
        assert fdekit._containers(f"fde-ex-{run_id}")
        kinds = [kind for _, kind, _ in fdekit._processes(f"fde-ex-{run_id}")]
        assert kinds.count("guard") == 1 and kinds.count("qemu") == 1
        os.kill(child.pid, signal.SIGKILL)
        child.wait(timeout=10)
        deadline = time.monotonic() + 15
        while fdekit.leftovers(run_id) and time.monotonic() < deadline:
            time.sleep(0.5)
        assert fdekit.leftovers(run_id) == []
    finally:
        if child.poll() is None:
            child.kill()
        if len(run_id) == 8:
            fdekit.clean(run_id)


def test_models_pinned():
    assert {"llm-small", "llm-medium", "embed-small"} <= fdekit.MODELS.keys()
    for weights in fdekit.MODELS.values():
        assert re.fullmatch(r"[0-9a-f]{40}", weights.revision)
        assert re.fullmatch(r"[0-9a-f]{64}", weights.sha256)
        assert weights.filename.endswith(".gguf")
    assert "q4_k_m" in fdekit.MODELS["llm-small"].filename.lower()
    assert "q4_k_m" in fdekit.MODELS["llm-medium"].filename.lower()
    assert fdekit.MODELS["llm-small"].repo == "Qwen/Qwen2.5-0.5B-Instruct-GGUF"


def test_fetch_model_rejects_bad_sha(tmp_path, monkeypatch):
    monkeypatch.setattr(fdekit, "MODEL_CACHE", tmp_path)
    monkeypatch.setattr(fdekit, "_download", lambda url, dest: dest.write_bytes(b"not the model"))
    with pytest.raises(RuntimeError, match="sha256"):
        fdekit.fetch_model("embed-small")
    assert [p.name for p in tmp_path.iterdir() if not p.name.endswith(".lock")] == []


def test_fetch_model_downloads_once_and_verifies(tmp_path, monkeypatch):
    payload = b"gguf-bytes"
    monkeypatch.setattr(fdekit, "MODEL_CACHE", tmp_path)
    monkeypatch.setitem(fdekit.MODELS, "embed-small", fdekit.Weights(
        "o/r", "m.gguf", "0" * 40, hashlib.sha256(payload).hexdigest()))
    urls = []
    monkeypatch.setattr(fdekit, "_download", lambda url, dest: urls.append(url) or dest.write_bytes(payload))
    path = fdekit.fetch_model("embed-small")
    assert fdekit.fetch_model("embed-small") == path and path.read_bytes() == payload
    assert urls == ["https://huggingface.co/o/r/resolve/" + "0" * 40 + "/m.gguf"]
