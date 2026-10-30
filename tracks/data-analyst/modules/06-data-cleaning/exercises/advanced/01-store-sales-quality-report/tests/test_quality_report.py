import re

import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
REPORT_HEADINGS = ["## Tóm tắt", "## Phạm vi và cách kiểm", "## Kết quả kiểm", "## Vấn đề và tác động",
                   "## Khuyến nghị", "## Giới hạn"]
RESULT_COLUMNS = ["name", "kind", "severity", "failed", "failed_share", "passed"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("quality_checks.ipynb")


def small():
    return pd.DataFrame({
        "Store": [1, 1, 2, 2, 3, 3],
        "Date": pd.to_datetime(["2015-01-01", "2015-01-02", "2015-01-01", "2015-01-01", "2015-01-01", "2015-01-02"]),
        "Sales": [100, 0, 50, -5, 80, None],
        "Open": [1, 1, 1, 0, 1, 1],
        "StateHoliday": ["0", "a", "0", "x", "0", "0"],
    })


CHECKS = [
    {"name": "sales_not_null", "kind": "not_null", "column": "Sales"},
    {"name": "key_unique", "kind": "unique", "columns": ["Store", "Date"], "severity": "error"},
    {"name": "sales_range", "kind": "range", "column": "Sales", "min": 0, "max": 1000, "severity": "warn"},
    {"name": "holiday_codes", "kind": "allowed", "column": "StateHoliday", "values": ["0", "a", "b", "c"]},
    {"name": "open_has_sales", "kind": "rule", "rule": "not (Open == 1 and Sales == 0)", "severity": "warn"},
]


def test_run_checks_table(nb):
    out = nb.run_checks(small(), CHECKS)
    assert list(out.columns) == RESULT_COLUMNS
    assert out["name"].tolist() == [c["name"] for c in CHECKS]
    assert out["kind"].tolist() == ["not_null", "unique", "range", "allowed", "rule"]
    assert out["severity"].tolist() == ["error", "error", "warn", "error", "warn"]   # mặc định "error"


def test_run_checks_counts(nb):
    out = nb.run_checks(small(), CHECKS).set_index("name")
    # not_null: 1 dòng Sales thiếu
    # unique: (2, 2015-01-01) xuất hiện 2 lần -> cả 2 dòng tính là lỗi
    # range: -5 ngoài [0, 1000]; ô thiếu không tính là lỗi range (đã có not_null)
    # allowed: "x"
    # rule: dòng Open == 1 và Sales == 0 (dòng 1); ô thiếu không làm rule lỗi
    assert out["failed"].tolist() == [1, 2, 1, 1, 1]
    assert out["failed_share"].tolist() == pytest.approx([1 / 6, 2 / 6, 1 / 6, 1 / 6, 1 / 6])
    assert not out["passed"].any()


def test_run_checks_pass(nb):
    clean = small().iloc[[0, 2, 4]]
    out = nb.run_checks(clean, CHECKS)
    assert out["failed"].tolist() == [0, 0, 0, 0, 0]
    assert out["passed"].all()


def test_run_checks_unknown_kind(nb):
    with pytest.raises(ValueError):
        nb.run_checks(small(), [{"name": "x", "kind": "regex", "column": "Sales"}])


def test_run_checks_does_not_mutate_input(nb):
    df = small()
    before = df.copy()
    nb.run_checks(df, CHECKS)
    pd.testing.assert_frame_equal(df, before)


def test_coverage_gaps(nb):
    df = pd.DataFrame({
        "Store": [1, 1, 1, 1, 2, 2, 3, 3, 3],
        "Date": pd.to_datetime(["2015-01-01", "2015-01-02", "2015-01-03", "2015-01-04",
                                "2015-01-01", "2015-01-04", "2015-01-02", "2015-01-03", "2015-01-04"]),
    })
    out = nb.coverage_gaps(df, "Store", "Date")
    assert list(out.columns) == ["missing_days", "first_missing", "last_missing"]
    assert out.index.name == "Store"
    assert list(out.index) == [2, 3]                                   # cửa hàng 1 đủ ngày: không có dòng
    assert out.loc[2].tolist() == [2, pd.Timestamp("2015-01-02"), pd.Timestamp("2015-01-03")]
    assert out.loc[3].tolist() == [1, pd.Timestamp("2015-01-01"), pd.Timestamp("2015-01-01")]


@pytest.fixture(scope="module")
def train():
    path = ex.dataset("store-sales") / "train.csv"
    return pd.read_csv(path, dtype={"StateHoliday": str}, parse_dates=["Date"])


def test_real_coverage(nb, train):
    gaps = nb.coverage_gaps(train, "Store", "Date")
    assert len(gaps) == 181
    assert (gaps["missing_days"] == 184).sum() == 180
    assert gaps.loc[988].tolist() == [1, pd.Timestamp("2013-01-01"), pd.Timestamp("2013-01-01")]


def test_real_checks(nb, train):
    checks = [
        {"name": "key_unique", "kind": "unique", "columns": ["Store", "Date"]},
        {"name": "holiday_codes", "kind": "allowed", "column": "StateHoliday", "values": ["0", "a", "b", "c"]},
        {"name": "open_has_sales", "kind": "rule", "rule": "not (Open == 1 and Sales == 0)", "severity": "warn"},
    ]
    out = nb.run_checks(train, checks).set_index("name")
    assert out.loc["key_unique", "failed"] == 0
    assert out.loc["holiday_codes", "failed"] == 0
    assert out.loc["open_has_sales", "failed"] == 54


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report, "Còn dòng TODO trong REPORT.md"
    words = len(report.split())
    assert 300 <= words <= 900, f"Báo cáo 300-900 từ, hiện có {words}"
    title = report.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline có con số"
    for heading in REPORT_HEADINGS:
        assert heading in report, f"Thiếu mục {heading}"
