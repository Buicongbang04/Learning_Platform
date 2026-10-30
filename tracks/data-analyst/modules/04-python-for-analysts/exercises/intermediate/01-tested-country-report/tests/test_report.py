import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


# Đọc sheet xlsx mất 20-90 giây: cache parquet trong thư mục tạm của hệ điều hành (không ghi vào data/raw),
# khoá theo mtime + size của tệp xlsx, ghi atomic. Cache giữ dữ liệu gốc của sheet (chưa làm sạch); Invoice,
# StockCode, Description ép str để ghi được parquet.
CACHE_DIR = Path(tempfile.gettempdir()) / "da-cache"


def read_retail_sheet(sheet: str = "Year 2010-2011") -> pd.DataFrame:
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    stat = xlsx.stat()
    cache = CACHE_DIR / f"online_retail_II-{sheet.replace(' ', '_')}-{stat.st_mtime_ns}-{stat.st_size}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    tx = pd.read_excel(xlsx, sheet_name=sheet)
    tx = tx.assign(Invoice=tx["Invoice"].astype(str), StockCode=tx["StockCode"].astype(str),
                   Description=tx["Description"].astype("string"))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
    tx.to_parquet(tmp, index=False)
    os.replace(tmp, cache)
    return tx
SUMMARY_COLUMNS = ["revenue", "orders", "customers", "aov", "share"]
COMPARE_COLUMNS = ["revenue", "revenue_prev", "change", "growth", "status"]
Q3, Q2 = ("2011-07-01", "2011-10-01"), ("2011-04-01", "2011-07-01")


@pytest.fixture(scope="module")
def report():
    return ex.module("report.py")


def make_tx(rows):
    return pd.DataFrame(rows, columns=["Invoice", "InvoiceDate", "Quantity", "Price", "Customer ID", "Country"]).assign(
        InvoiceDate=lambda d: pd.to_datetime(d["InvoiceDate"], format="ISO8601"))


def tiny_tx():
    return make_tx([
        (100, "2011-01-10", 2, 10.0, 1.0, "France"),
        (100, "2011-01-10", 1, 5.0, 1.0, "France"),
        ("C101", "2011-01-11", -1, 5.0, 1.0, "France"),
        (102, "2011-01-12", 4, 0.0, 2.0, "France"),
        (103, "2011-01-20", 1, 30.0, np.nan, "Spain"),
        (104, "2011-02-01", 3, 10.0, 1.0, "France"),
        (105, "2011-02-03", 1, 6.0, 3.0, "France"),
        (105, "2011-02-03", -2, 6.0, 3.0, "France"),
        (106, "2011-02-10", 2, 20.0, 4.0, "Japan"),
        (107, "2011-02-28 23:59", 1, 4.0, 5.0, "Japan"),
        (108, "2011-03-01 00:00", 9, 9.0, 5.0, "Japan"),
    ])


# ---------- report.py ----------

def test_clean_transactions(report):
    tx = tiny_tx()
    before = tx.copy()
    sales = report.clean_transactions(tx)
    pd.testing.assert_frame_equal(tx, before)
    assert sales["Invoice"].tolist() == ["100", "100", "103", "104", "105", "106", "107", "108"]
    assert sales["revenue"].tolist() == pytest.approx([20, 5, 30, 30, 6, 40, 4, 81])


def test_country_summary(report):
    out = report.country_summary(tiny_tx(), "2011-02-01", "2011-03-01")
    assert list(out.columns) == SUMMARY_COLUMNS
    assert list(out.index) == ["Japan", "France"]
    assert out.loc["Japan"].tolist() == pytest.approx([44.0, 2, 2, 22.0, 44 / 80])
    assert out.loc["France"].tolist() == pytest.approx([36.0, 2, 2, 18.0, 36 / 80])
    jan = report.country_summary(tiny_tx(), "2011-01-01", "2011-02-01")
    assert jan.loc["Spain", "customers"] == 0 and jan.loc["Spain", "orders"] == 1
    assert jan.loc["France", "revenue"] == pytest.approx(25.0)


def test_compare_periods(report):
    out = report.compare_periods(tiny_tx(), current=("2011-02-01", "2011-03-01"), previous=("2011-01-01", "2011-02-01"))
    assert list(out.columns) == COMPARE_COLUMNS
    assert list(out.index) == ["Japan", "France", "Spain"]
    assert out.loc["Japan", ["revenue", "revenue_prev", "change", "status"]].tolist() == [44.0, 0.0, 44.0, "new"]
    assert np.isnan(out.loc["Japan", "growth"])
    assert out.loc["France", ["revenue_prev", "growth", "status"]].tolist() == pytest.approx([25.0, 0.44, "both"])
    assert out.loc["Spain", ["revenue", "growth", "status"]].tolist() == [0.0, -1.0, "lost"]


def test_compare_periods_top_other(report):
    out = report.compare_periods(tiny_tx(), current=("2011-02-01", "2011-03-01"),
                                 previous=("2011-01-01", "2011-02-01"), top=1)
    assert list(out.index) == ["Japan", "Other"]
    other = out.loc["Other"]
    assert other[["revenue", "revenue_prev", "change", "status"]].tolist() == pytest.approx([36.0, 55.0, -19.0, "other"])
    assert other["growth"] == pytest.approx(36 / 55 - 1)


# ---------- test của người học: chạy trên report.py của bạn và trên 4 bản bị làm hỏng ----------

MUTANTS = {
    "không bỏ hoá đơn huỷ và dòng số lượng âm": '''
def clean_transactions(tx):
    sales = tx.assign(Invoice=tx["Invoice"].astype(str))
    sales = sales[sales["Price"] > 0].copy()
    sales["revenue"] = sales["Quantity"] * sales["Price"]
    return sales
''',
    "orders và customers đếm số dòng thay vì giá trị khác nhau": '''
_orig_country_summary = country_summary
def country_summary(tx, start, end):
    out = _orig_country_summary(tx, start, end).copy()
    sales = clean_transactions(tx)
    sales = sales[(sales["InvoiceDate"] >= pd.Timestamp(start)) & (sales["InvoiceDate"] < pd.Timestamp(end))]
    rows = sales.groupby("Country").size().reindex(out.index)
    out["orders"] = rows
    out["customers"] = sales.groupby("Country")["Customer ID"].count().reindex(out.index)
    return out
''',
    "so hai kỳ bằng inner join, mất nước mới và nước mất": '''
_orig_compare_periods = compare_periods
def compare_periods(tx, current, previous, top=None):
    out = _orig_compare_periods(tx, current, previous, top=top)
    return out[(out["revenue"] > 0) & (out["revenue_prev"] > 0)]
''',
    "tăng trưởng chia cho kỳ này thay vì kỳ trước": '''
_orig_compare_periods = compare_periods
def compare_periods(tx, current, previous, top=None):
    out = _orig_compare_periods(tx, current, previous, top=top).copy()
    out["growth"] = out["change"] / out["revenue"]
    return out
''',
}


def run_checks(tmp_path, report_source):
    (tmp_path / "report.py").write_text(report_source, encoding="utf-8")
    shutil.copy(ex.path("checks_report.py"), tmp_path / "checks_report.py")
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(tmp_path)}
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "checks_report.py"],
                          cwd=tmp_path, capture_output=True, text=True, timeout=120, env=env)
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", proc.stdout)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", proc.stdout)) else 0
    return proc, passed, failed


def test_checks_has_enough_tests():
    tree = ast.parse(ex.read("checks_report.py"))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    assert len(names) >= 4, f"checks_report.py cần ít nhất 4 hàm test_*, hiện có {len(names)}: {names}"


def test_checks_pass_on_your_report(tmp_path):
    proc, passed, failed = run_checks(tmp_path, ex.read("report.py"))
    assert proc.returncode == 0 and failed == 0 and passed >= 4, (
        f"Test của bạn phải pass trên report.py của bạn ({passed} pass, {failed} fail):\n{proc.stdout[-3000:]}")


_BASELINE = {}


def baseline_ok(tmp_path_factory):
    """Test của bạn có pass trên report.py của bạn không (chạy một lần)."""
    if "ok" not in _BASELINE:
        _, passed, failed = run_checks(tmp_path_factory.mktemp("baseline"), ex.read("report.py"))
        _BASELINE["ok"] = failed == 0 and passed >= 4
    return _BASELINE["ok"]


@pytest.mark.parametrize("bug", list(MUTANTS), ids=["cancellations", "count-not-nunique", "inner-join", "growth-denominator"])
def test_checks_catch_bug(tmp_path, tmp_path_factory, bug):
    assert baseline_ok(tmp_path_factory), (
        "Trước hết checks_report.py phải có >= 4 test và pass hết trên report.py của bạn "
        "(xem test_checks_pass_on_your_report)")
    source = ex.read("report.py") + "\n\n# ---- lỗi cố ý ----\n" + MUTANTS[bug]
    proc, passed, failed = run_checks(tmp_path, source)
    assert failed >= 1, f"Không test nào trong checks_report.py bắt được lỗi: {bug}"


# ---------- dữ liệu thật ----------

@pytest.fixture(scope="module")
def real_tx():
    return read_retail_sheet("Year 2010-2011")


def test_real_country_summary(report, real_tx):
    out = report.country_summary(real_tx, *Q3)
    assert len(out) == 30
    assert out["revenue"].sum() == pytest.approx(2_536_949.74, abs=1)
    uk = out.loc["United Kingdom"]
    assert (uk["orders"], uk["customers"]) == (4192, 1939)
    assert uk["share"] == pytest.approx(0.8306, abs=1e-4)
    assert out.index[1] == "EIRE" and out.loc["EIRE", "customers"] == 3


def test_real_compare_periods(report, real_tx):
    out = report.compare_periods(real_tx, current=Q3, previous=Q2)
    assert len(out) == 33
    assert out["status"].value_counts().to_dict() == {"both": 29, "lost": 3, "new": 1}
    assert set(out[out.status == "lost"].index) == {"Bahrain", "Brazil", "USA"}
    assert out.loc["United Kingdom", "growth"] == pytest.approx(0.2142, abs=1e-4)
    top = report.compare_periods(real_tx, current=Q3, previous=Q2, top=5)
    assert list(top.index) == ["United Kingdom", "EIRE", "Netherlands", "Germany", "France", "Other"]
    assert top.loc["Other", "revenue"] == pytest.approx(157_317.55, abs=1)
    assert top["revenue_prev"].sum() == pytest.approx(2_070_084.54, abs=1)
