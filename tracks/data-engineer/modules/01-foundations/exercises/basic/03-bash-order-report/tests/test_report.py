import os
import shutil
import subprocess

import pytest

from testkit import Exercise

ex = Exercise(__file__)

BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="Cần bash")


def run(*args, cwd=None):
    env = {**os.environ, "LC_ALL": "C"}
    return subprocess.run(
        [BASH, str(ex.path("report.sh")), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        cwd=cwd,
    )


def test_counts_fixture():
    result = run(ex.fixtures / "orders.csv")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "order_status,count",
        "delivered,5",
        "shipped,2",
        "canceled,1",
        "invoiced,1",
    ]


def test_total_goes_to_stderr():
    result = run(ex.fixtures / "orders.csv")
    assert "total=9" in result.stderr
    assert "total=" not in result.stdout


def test_status_column_found_by_name(tmp_path):
    path = tmp_path / "orders reordered.csv"   # có dấu cách: kiểm tra quote biến
    path.write_text(
        "order_status,order_id,order_purchase_timestamp\n"
        "shipped,o1,2018-01-01\n"
        "approved,o2,2018-01-02\n"
        "shipped,o3,2018-01-03\n"
        "approved,o4,2018-01-04\n"
        "delivered,o5,2018-01-05\n",
        encoding="utf-8",
    )
    result = run(path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "order_status,count",
        "approved,2",
        "shipped,2",
        "delivered,1",
    ]
    assert "total=5" in result.stderr


def test_usage_without_args():
    result = run()
    assert result.returncode == 2
    assert result.stderr.lstrip().startswith("Usage:")
    assert result.stdout == ""


def test_missing_file(tmp_path):
    result = run(tmp_path / "nope.csv")
    assert result.returncode == 1
    assert result.stderr.strip() != ""
    assert result.stdout == ""


def test_missing_status_column(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("order_id,customer_id\no1,c1\n", encoding="utf-8")
    result = run(path)
    assert result.returncode == 1
    assert result.stdout == ""


def test_strict_mode():
    script = ex.read("report.sh")
    assert "set -euo pipefail" in script
