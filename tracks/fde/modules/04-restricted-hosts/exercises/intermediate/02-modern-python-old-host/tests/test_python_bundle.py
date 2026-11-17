import csv
import datetime
import hashlib
import json
import random
import shutil
import socket
import subprocess
import tarfile
from collections import Counter
from pathlib import Path

import pytest

import fdekit
from testkit import ROOT, Exercise, run_sandboxed

ex = Exercise(__file__)
APP = ex.dir / "app"
TOOLS = ROOT / "data" / "raw" / "fde-tools"
PBS_TAG = "20261021"
PBS_NAME = f"cpython-3.12.15+{PBS_TAG}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
PBS = TOOLS / f"python-build-standalone-{PBS_TAG}" / PBS_NAME
PBS_SHA256 = "6d7521138fd33afddc1ccd08abb007d9a2829e38117c2576f9efdc0ec73ce772"
PBS_URL = (f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_TAG}/"
           + PBS_NAME.replace("+", "%2B"))
PINS = {"pydantic": "2.11.7", "pydantic_core": "2.33.2"}
BUILD_TIMEOUT = 240
INSTALL_TIMEOUT = 150
CENSUS = "/home/fde/.local/bin/census"
GUARDED = "/usr/local /opt /etc/environment /etc/profile.d"


def require_inputs() -> None:
    if not PBS.is_file():
        pytest.skip(f"Chưa có {PBS.relative_to(ROOT)}. Tải một lần: mkdir -p {PBS.parent.relative_to(ROOT)} && "
                    f"curl -fLo '{PBS.relative_to(ROOT)}' '{PBS_URL}' && echo '{PBS_SHA256}  "
                    f"{PBS.relative_to(ROOT)}' | sha256sum -c -")
    with PBS.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != PBS_SHA256:
            pytest.skip(f"{PBS.relative_to(ROOT)} sai sha256; xoá rồi tải lại theo phần '0. Cài đặt' của README module")
    try:
        socket.create_connection(("pypi.org", 443), timeout=5).close()
    except OSError:
        pytest.skip("Bước build bundle chạy trên máy bạn và cần tải wheel từ pypi.org; máy đang không ra được mạng")
    if not shutil.which("uv"):
        pytest.skip("Chưa có uv trên PATH (xem README gốc của repo)")


def build(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    shutil.copytree(APP, work / "app", ignore=shutil.ignore_patterns(".venv", "dist", "__pycache__"))
    try:
        result = run_sandboxed(["sh", ex.path("build_bundle.sh"), work / "app", TOOLS, work / "bundle"],
                               writable=[work], cwd=work, env={}, timeout=BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        pytest.fail(f"build_bundle.sh chạy quá {BUILD_TIMEOUT} s")
    assert result.returncode == 0, f"build_bundle.sh thoát mã {result.returncode}\nstderr:\n{result.stderr[-3000:]}"
    assert (work / "bundle" / "install.sh").is_file(), "Bundle phải có install.sh ở thư mục gốc"
    archive = tmp_path / "census-bundle.tar"
    with tarfile.open(archive, "w") as tar:
        tar.add(work / "bundle", "census-bundle")
    return archive


def admissions(rng: random.Random) -> tuple[list[dict], str, dict[str, int]]:
    wards = rng.sample(["noi-a", "noi-b", "ngoai", "san", "nhi", "hoi-suc", "tim-mach", "than"], rng.randint(3, 6))
    start = datetime.date(2026, 1, 1)
    rows = []
    for i in range(rng.randint(150, 400)):
        admitted = start + datetime.timedelta(days=rng.randrange(300))
        stay = rng.choice([None, rng.randint(1, 40)])
        discharged = admitted + datetime.timedelta(days=stay) if stay else None
        rows.append({"patient": f"BN{rng.getrandbits(32):08x}", "ward": rng.choice(wards),
                     "admitted": admitted.isoformat(), "discharged": discharged.isoformat() if discharged else ""})
    day = start + datetime.timedelta(days=rng.randrange(60, 320))
    counts = Counter(r["ward"] for r in rows if datetime.date.fromisoformat(r["admitted"]) <= day
                     and (not r["discharged"] or datetime.date.fromisoformat(r["discharged"]) > day))
    return rows, day.isoformat(), dict(sorted(counts.items()))


def sh(m, cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return m.ssh(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        pytest.fail(f"Lệnh trong VM chạy quá {timeout:.0f} s (đang chờ mạng?): {cmd[:150]}")


def guarded(m) -> str:
    return sh(m, f"find {GUARDED} -xdev \\( -type f -o -type l \\) 2>/dev/null | sort | xargs -r sha256sum 2>/dev/null; "
                 "/usr/bin/python3 -V").stdout


def install(m, attempt: str) -> None:
    run = sh(m, "cd /tmp && sh /home/fde/census-bundle/install.sh", timeout=INSTALL_TIMEOUT)
    assert run.returncode == 0, (
        f"install.sh ({attempt}) thoát mã {run.returncode} trên hospital\nstdout:\n{run.stdout[-2000:]}\n"
        f"stderr:\n{run.stderr[-3000:]}")


def check_run(m, command: str, want: dict[str, int], rows: int, how: str) -> None:
    ran = sh(m, command, timeout=60)
    assert ran.returncode == 0, f"census ({how}) lỗi mã {ran.returncode}:\n{ran.stderr[-2000:]}"
    got = json.loads(ran.stdout)
    assert got.get("occupied") == want and got.get("records") == rows, f"census ({how}) cho kết quả sai: app cài chưa đúng"
    versions = got.get("versions", {})
    assert str(versions.get("python", "")).startswith("3.12."), (
        f"census ({how}) chạy bằng Python {versions.get('python')}, cần 3.12")
    for name, pin in PINS.items():
        assert versions.get(name) == pin, f"{name} trong môi trường cài là {versions.get(name)}, uv.lock ghim {pin}"
    real = sh(m, f"readlink -f {json.dumps(got.get('executable', ''))}").stdout.strip()
    assert real.startswith("/home/fde/"), f"Python chạy census phải nằm trong /home/fde, đang là {real or got.get('executable')}"


def test_python312_app_on_hospital(tmp_path):
    require_inputs()
    archive = build(tmp_path)
    rng = random.Random(random.SystemRandom().randrange(1 << 30))
    rows, day, want = admissions(rng)
    data = tmp_path / "admissions.csv"
    with data.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["patient", "ward", "admitted", "discharged"])
        writer.writeheader()
        writer.writerows(rows)
    with fdekit.vm("hospital", memory_mb=1024) as m:
        m.put(archive, "/home/fde/census-bundle.tar")
        m.put(data, "/home/fde/admissions.csv")
        assert sh(m, "tar -xf /home/fde/census-bundle.tar -C /home/fde").returncode == 0
        before = guarded(m)
        install(m, "lần 1")
        install(m, "lần 2")
        check_run(m, f"{CENSUS} /home/fde/admissions.csv {day}", want, len(rows), "phiên đăng nhập")
        check_run(m, f"cd / && env -i HOME=/home/fde PATH=/usr/bin:/bin {CENSUS} /home/fde/admissions.csv {day}",
                  want, len(rows), "env -i, PATH tối thiểu")
        assert guarded(m) == before, (
            "Máy bệnh viện đã bị đổi ngoài $HOME (/usr/local, /opt, /etc/environment, /etc/profile.d, hay Python hệ thống)")
