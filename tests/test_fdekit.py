import hashlib
import os
import signal
import subprocess
import sys
import time
from io import BytesIO

import pycdlib
import pytest

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


def test_netdev_args(monkeypatch):
    arg = fdekit._netdev(ssh_port=2222, forwards={8000: 31000}, guestfwds={"10.0.2.100:3128": 41000}, restrict=True)
    assert arg.startswith("user,id=n0,restrict=on,")
    assert "hostfwd=tcp:127.0.0.1:2222-:22" in arg
    assert "hostfwd=tcp:127.0.0.1:31000-:8000" in arg
    assert "guestfwd=tcp:10.0.2.100:3128-tcp:127.0.0.1:41000" in arg
    assert "restrict=off" in fdekit._netdev(ssh_port=2222, forwards={}, guestfwds={}, restrict=False)


def test_clean_rejects_bad_run_id():
    for bad in ("", "*", "../x", "fde-ex-", "abc"):
        with pytest.raises(ValueError):
            fdekit.clean(bad)


def test_leftovers_reports_run_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(fdekit, "LAB", tmp_path)
    (tmp_path / "fde-ex-0badc0de").mkdir()
    (tmp_path / "fde-ex-12345678").mkdir()
    monkeypatch.setattr(fdekit, "_containers", lambda needle: [])
    assert fdekit.leftovers("0badc0de") == [str(tmp_path / "fde-ex-0badc0de")]
    assert len(fdekit.leftovers()) == 2
    fdekit.clean("0badc0de")
    assert fdekit.leftovers("0badc0de") == []
    assert (tmp_path / "fde-ex-12345678").exists()


def test_cli_prepare_not_ready(capsys):
    code = fdekit.main(["prepare", "lab-open"])
    assert code != 0
    assert "lab-open" in capsys.readouterr().err


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


def _ubuntu():
    fdekit.require_kvm()
    return fdekit.fetch_image("ubuntu-22.04")


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


def test_vm_put_get(tmp_path):
    base = _ubuntu()
    source = tmp_path / "hello.txt"
    source.write_text("xin chào\n")
    with fdekit.vm(None, base=base, memory_mb=1024) as m:
        m.put(source, "/home/fde/hello.txt")
        assert m.ssh("cat /home/fde/hello.txt").stdout == "xin chào\n"
        m.get("/etc/hostname", tmp_path / "hostname")
    assert (tmp_path / "hostname").read_text().strip()


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
