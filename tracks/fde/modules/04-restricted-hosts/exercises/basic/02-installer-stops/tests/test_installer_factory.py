import hashlib
import io
import json
import random
import subprocess
import tarfile
from pathlib import Path

import pytest

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
TOOL = ex.dir / "fieldsync" / "fieldsync.py"
NAME = "fieldsync-1.4.0"
WORK = "/home/fde/fs"
PREFIX = "/home/fde/fieldsync"
INSTALL_TIMEOUT = 120
GUARDED = "/etc/fstab /etc/security/limits.conf /etc/security/limits.d /etc/systemd/system.conf.d /etc/systemd/user.conf.d"


def make_assets(rng: random.Random) -> dict[str, bytes]:
    folders = [f"{rng.choice(['may', 'line', 'qc', 'kho'])}-{i:02d}" for i in range(rng.randint(8, 14))]
    assets = {}
    while len(assets) < rng.randint(1100, 1400):
        name = f"{rng.choice(folders)}/{rng.getrandbits(40):010x}.txt"
        assets[name] = f"{name}\n{rng.getrandbits(256):064x}\n".encode() * rng.randint(1, 8)
    return assets


def make_bundle(path: Path, assets: dict[str, bytes]) -> None:
    def add(tar: tarfile.TarFile, name: str, data: bytes, mode: int) -> None:
        info = tarfile.TarInfo(f"{NAME}/{name}")
        info.size, info.mode, info.mtime = len(data), mode, 1767225600
        tar.addfile(info, io.BytesIO(data))

    with tarfile.open(path, "w") as tar:
        add(tar, "bin/fieldsync", TOOL.read_bytes(), 0o755)
        for name, data in sorted(assets.items()):
            add(tar, f"assets/{name}", data, 0o644)


def sh(m, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s: {cmd[:150]}")


def guarded(m) -> str:
    return sh(m, f"find {GUARDED} -type f -exec sha256sum {{}} + 2>/dev/null | sort; findmnt -no OPTIONS /tmp").stdout


def install(m, bundle: str, limit: int | None, attempt: str) -> None:
    prefix = f"ulimit -n {limit} && " if limit else ""
    run = sh(m, f"{prefix}cd /tmp && sh {WORK}/install.sh {WORK}/{bundle}", timeout=INSTALL_TIMEOUT)
    assert run.returncode == 0, (
        f"install.sh ({attempt}) thoát mã {run.returncode}\nstdout:\n{run.stdout[-1500:]}\nstderr:\n{run.stderr[-2500:]}")


def check_installed(m, assets: dict[str, bytes], tmp_path: Path, attempt: str) -> None:
    local = tmp_path / f"index-{attempt}.json"
    got = sh(m, f"cat {PREFIX}/index.json")
    assert got.returncode == 0, f"{attempt}: không đọc được {PREFIX}/index.json"
    local.write_text(got.stdout)
    index = json.loads(local.read_text())
    want = {name: hashlib.sha256(data).hexdigest() for name, data in assets.items()}
    assert index.get("count") == len(want), f"{attempt}: index.json có count {index.get('count')}, cần {len(want)}"
    assert index.get("files") == want, f"{attempt}: index.json không khớp bộ tài liệu của bundle vừa cài"
    listed = sh(m, f"cd {PREFIX}/assets && find . -type f | sed 's|^\\./||' | sort").stdout.split()
    assert listed == sorted(want), (
        f"{attempt}: {PREFIX}/assets phải đúng bộ tài liệu của bundle vừa cài "
        f"(thừa {len(set(listed) - set(want))}, thiếu {len(set(want) - set(listed))})")
    version = sh(m, f"{PREFIX}/bin/fieldsync --version")
    assert version.returncode == 0 and version.stdout.strip() == "fieldsync 1.4.0", (
        f"{attempt}: {PREFIX}/bin/fieldsync --version lỗi:\n{version.stderr[-500:]}")


def test_install_on_factory(tmp_path):
    rng = random.Random(random.SystemRandom().randrange(1 << 30))
    first, second = make_assets(rng), make_assets(rng)
    make_bundle(tmp_path / "a.tar", first)
    make_bundle(tmp_path / "b.tar", second)
    limit = rng.randint(400, 700)
    with fdekit.vm("factory", memory_mb=1024) as m:
        assert sh(m, f"mkdir -p {WORK}").returncode == 0
        m.put(tmp_path / "a.tar", f"{WORK}/{NAME}.tar")
        m.put(tmp_path / "b.tar", f"{WORK}/{NAME}-thang-sau.tar")
        m.put(ex.path("install.sh"), f"{WORK}/install.sh")
        before = guarded(m)

        install(m, f"{NAME}.tar", None, "lần 1")
        check_installed(m, first, tmp_path, "lần 1")
        install(m, f"{NAME}-thang-sau.tar", limit, f"lần 2, ulimit -n {limit}")
        check_installed(m, second, tmp_path, "lần 2")

        assert guarded(m) == before, (
            "Cấu hình hệ thống của xưởng đã bị đổi (fstab, limits, systemd, hay mount /tmp); bài này chỉ được cài vào $HOME")
        hard = sh(m, "ulimit -Hn").stdout.strip()
        assert hard == "1024", f"Phiên đăng nhập mới có ulimit -Hn {hard}, IT xưởng đặt 1024 và không cho đổi"
