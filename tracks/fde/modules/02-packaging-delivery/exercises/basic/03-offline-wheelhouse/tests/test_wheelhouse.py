import json
import random
import shutil
import socket
import subprocess
import tarfile
import uuid

import pytest
import yaml

import fdekit
from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
APP = ex.dir / "app"
PINS = {"pydantic": "2.11.7", "pyyaml": "6.0.2"}
BUILD_TIMEOUT = 240
INSTALL_TIMEOUT = 120


def require_index() -> None:
    try:
        socket.create_connection(("pypi.org", 443), timeout=5).close()
    except OSError:
        pytest.skip("Bước build bundle chạy trên máy bạn và cần tải wheel từ pypi.org; máy đang không ra được mạng")
    if not shutil.which("uv"):
        pytest.skip("Chưa có uv trên PATH (xem README gốc của repo)")


def build(tmp_path):
    work = tmp_path / "work"
    shutil.copytree(APP, work / "app", ignore=shutil.ignore_patterns(".venv", "dist", "__pycache__"))
    try:
        result = run_sandboxed(["sh", ex.path("build_bundle.sh"), work / "app", work / "bundle"], writable=[work],
                               cwd=work, env={}, timeout=BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        pytest.fail(f"build_bundle.sh chạy quá {BUILD_TIMEOUT} s")
    assert result.returncode == 0, f"build_bundle.sh thoát mã {result.returncode}\nstderr:\n{result.stderr[-3000:]}"
    bundle = work / "bundle"
    assert (bundle / "install.sh").is_file(), "Bundle phải có install.sh ở thư mục gốc"
    archive = tmp_path / "intake-bundle.tar"
    with tarfile.open(archive, "w") as tar:
        tar.add(bundle, "intake-bundle")
    return archive


def documents(seed: int) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    pool = ["hop-dong", "phu-luc", "bao-mat", "nhan-su", "tai-chinh", "mat"]
    docs = [{"id": uuid.UUID(int=rng.getrandbits(128)).hex[:8], "title": f"Tài liệu {i}", "pages": rng.randint(1, 90),
             "tags": rng.sample(pool, rng.randint(0, 3))} for i in range(rng.randint(5, 25))]
    want = {"documents": len(docs), "pages": sum(d["pages"] for d in docs),
            "tags": sorted({t for d in docs for t in d["tags"]})}
    return docs, want


def test_offline_install_on_lawfirm_staging(tmp_path):
    require_index()
    archive = build(tmp_path)
    docs, want = documents(random.SystemRandom().randrange(1 << 30))
    data = tmp_path / "docs.yaml"
    data.write_text(yaml.safe_dump(docs, allow_unicode=True), encoding="utf-8")
    with fdekit.vm("lawfirm-staging", memory_mb=1024) as m:
        m.put(archive, "/home/fde/intake-bundle.tar")
        m.put(data, "/home/fde/docs.yaml")
        assert m.ssh("tar -xf /home/fde/intake-bundle.tar -C /home/fde", timeout=60).returncode == 0
        try:
            installed = m.ssh("cd /tmp && sh /home/fde/intake-bundle/install.sh", timeout=INSTALL_TIMEOUT)
        except subprocess.TimeoutExpired:
            pytest.fail(f"install.sh chạy quá {INSTALL_TIMEOUT} s trong VM (đang chờ mạng?)")
        assert installed.returncode == 0, (
            f"install.sh thoát mã {installed.returncode} trên lawfirm-staging\nstdout:\n{installed.stdout[-2000:]}\n"
            f"stderr:\n{installed.stderr[-3000:]}")
        system_python = m.ssh("/usr/bin/python3 -c 'import platform; print(platform.python_version())'",
                              timeout=30).stdout.strip()
        ran = m.ssh("/home/fde/intake/bin/intake /home/fde/docs.yaml", timeout=60)
    assert ran.returncode == 0, f"~/intake/bin/intake lỗi:\n{ran.stderr[-2000:]}"
    got = json.loads(ran.stdout)
    assert {k: got.get(k) for k in want} == want, "Kết quả của intake sai: app cài chưa đúng"
    versions = got.get("versions", {})
    assert versions.get("python") == system_python, (
        f"intake chạy bằng Python {versions.get('python')}, cần Python của hệ điều hành ({system_python})")
    for name, pin in PINS.items():
        assert versions.get(name) == pin, f"{name} trong môi trường cài là {versions.get(name)}, uv.lock ghim {pin}"
