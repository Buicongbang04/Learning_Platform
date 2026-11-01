import os
import shutil
import time
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def sb():
    return ex.module("sandbox.py")


TASKS = Path(__file__).resolve().parent.parent / "starter" / "tasks"


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_safe_path(sb, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    assert sb.safe_path(root, "a/b.py") == (root / "a" / "b.py").resolve()
    assert sb.safe_path(root, "a/../b.py") == (root / "b.py").resolve()
    for bad in ["../x.py", "a/../../x.py", "/etc/passwd", ""]:
        with pytest.raises(ValueError):
            sb.safe_path(root, bad)
    (tmp_path / "outside").mkdir()
    os.symlink(tmp_path / "outside", root / "link")
    with pytest.raises(ValueError):
        sb.safe_path(root, "link/secret.txt")


def test_run_pytest_counts(sb, tmp_path):
    write(tmp_path, "tests/test_a.py", "def test_1(): assert 1\ndef test_2(): assert 0\ndef test_3(): assert 1\n")
    run = sb.run_pytest(tmp_path, timeout=30)
    assert (run.passed, run.failed, run.errors, run.timed_out) == (2, 1, 0, False)
    assert run.ok is False and run.returncode == 1
    assert "test_2" in run.output
    write(tmp_path, "tests/test_a.py", "def test_1(): assert 1\n")
    run = sb.run_pytest(tmp_path, timeout=30)
    assert (run.passed, run.failed, run.errors) == (1, 0, 0) and run.ok


def test_run_pytest_collection_error(sb, tmp_path):
    write(tmp_path, "tests/test_a.py", "import khong_co_module\n")
    run = sb.run_pytest(tmp_path, timeout=30)
    assert run.errors == 1 and run.passed == 0 and not run.ok


def test_run_pytest_imports_from_workdir(sb, tmp_path):
    write(tmp_path, "money.py", "def f():\n    return 42\n")
    write(tmp_path, "tests/test_m.py", "from money import f\n\ndef test_f():\n    assert f() == 42\n")
    assert sb.run_pytest(tmp_path, timeout=30).ok


def test_run_pytest_timeout_kills_process_group(sb, tmp_path):
    marker = tmp_path / "still_running"
    write(tmp_path, "tests/test_loop.py",
          "import subprocess, sys, time\n"
          "def test_forever():\n"
          f"    subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3); open(r\"{marker}\", \"w\").write(\"x\")'])\n"
          "    while True:\n        time.sleep(0.1)\n")
    start = time.monotonic()
    run = sb.run_pytest(tmp_path, timeout=2)
    assert run.timed_out and run.returncode is None and not run.ok
    assert time.monotonic() - start < 8
    time.sleep(3.5)
    assert not marker.exists(), "quá thời gian phải giết cả nhóm tiến trình, kể cả tiến trình cháu"


def test_run_pytest_env_is_minimal(sb, tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_API_KEY", "sk-khong-duoc-lot")
    write(tmp_path, "tests/test_env.py",
          "import os\ndef test_env():\n    assert 'SECRET_API_KEY' not in os.environ\n"
          f"    assert os.environ['HOME'] == {str(tmp_path)!r}\n")
    assert sb.run_pytest(tmp_path, timeout=30).ok


def test_run_pytest_network(sb, tmp_path):
    write(tmp_path, "tests/test_net.py",
          "import socket\ndef test_net():\n    s = socket.socket()\n    s.settimeout(2)\n"
          "    assert s.connect_ex(('1.1.1.1', 80)) != 0\n")
    if not sb.network_isolation_available():
        pytest.skip("máy này không có unshare -rn")
    run = sb.run_pytest(tmp_path, timeout=30)
    assert run.network_isolated and run.ok, "trong sandbox không kết nối ra ngoài được"


def test_grade_uses_hidden_tests_not_agent_tests(sb, tmp_path):
    tasks = sorted(p for p in TASKS.iterdir() if p.is_dir() and p.name[:2].isdigit())
    assert len(tasks) == 12
    for t in tasks:
        assert (t / "TASK.md").exists() and (t / "hidden" / "test_hidden.py").exists()
        assert (t / "repo" / "tests" / "test_visible.py").exists()
    task = TASKS / "03-fix-median"
    work = tmp_path / "work"
    shutil.copytree(task / "repo", work)
    assert not sb.grade(task, work).ok, "mã gốc có bug: test ẩn phải fail"
    write(work, "tests/test_visible.py", "def test_ok():\n    assert True\n")
    assert sb.run_pytest(work, timeout=30).ok
    assert not sb.grade(task, work).ok, "agent sửa test của nó không được làm đổi kết quả chấm"
    write(work, "stats.py", "def median(values):\n    if not values:\n        raise ValueError('rỗng')\n"
                            "    o = sorted(values)\n    n = len(o)\n"
                            "    return o[n // 2] if n % 2 else (o[n // 2 - 1] + o[n // 2]) / 2\n")
    run = sb.grade(task, work)
    assert run.ok and run.passed == 5
    assert (work / "tests" / "test_visible.py").read_text() == "def test_ok():\n    assert True\n", "không sửa workdir"


def test_report_written():
    import re

    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 500, "báo cáo: ít nhất 500 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần bảng kết quả"


def test_grade_ignores_hook_files(sb, tmp_path):
    task = TASKS / "03-fix-median"
    work = tmp_path / "work"
    shutil.copytree(task / "repo", work)
    write(work, "conftest.py", "import pytest\n\n\n@pytest.hookimpl(hookwrapper=True)\n"
                               "def pytest_runtest_makereport(item, call):\n    outcome = yield\n"
                               "    outcome.get_result().outcome = 'passed'\n")
    write(work, "sitecustomize.py", "import builtins\n")
    assert sb.run_pytest(work, timeout=30).ok, "conftest.py của agent làm test thấy được 'pass' dù mã còn bug"
    assert not sb.grade(task, work).ok, "grade không được chép conftest.py/sitecustomize.py của agent"
