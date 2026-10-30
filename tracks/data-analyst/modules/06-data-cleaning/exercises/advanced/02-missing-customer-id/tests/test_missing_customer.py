import os
import re
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
MEMO_HEADINGS = ["## Trả lời ngắn", "## Bằng chứng", "## Cơ chế thiếu", "## Ảnh hưởng tới chỉ số",
                 "## Khuyến nghị", "## Giới hạn"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("missing_customer.ipynb")


def lines():
    nan = np.nan
    return pd.DataFrame({
        "Invoice": ["1", "1", "2", "2", "2", "3", "4", "4", "5"],
        "Quantity": [2, 1, 1, 1, 1, 10, 3, 1, 4],
        "Price": [1.5, 4.0, 3.0, 2.0, 5.0, 0.5, 2.0, 2.0, 1.0],
        "InvoiceDate": pd.to_datetime(["2011-01-03 09:10", "2011-01-03 09:10", "2011-01-03 16:40", "2011-01-03 16:41",
                                       "2011-01-03 16:41", "2011-01-04 11:00", "2011-01-04 17:05", "2011-01-04 17:05",
                                       "2011-01-05 10:00"]),
        "Customer ID": [100.0, 100.0, nan, nan, nan, 101.0, nan, 102.0, 100.0],
        "Country": ["UK", "UK", "UK", "UK", "UK", "France", "UK", "UK", "France"],
    })


def test_missing_profile(nb):
    out = nb.missing_profile(lines(), "Customer ID", "Country")
    assert list(out.columns) == ["rows", "missing", "missing_rate"]
    assert out.index.name == "Country"
    assert list(out.index) == ["UK", "France"]                       # sắp theo số dòng giảm dần
    assert out.loc["UK"].tolist() == pytest.approx([7, 4, 4 / 7])
    assert out.loc["France"].tolist() == pytest.approx([2, 0, 0.0])


def test_missing_profile_tie_and_types(nb):
    df = pd.DataFrame({"g": ["b", "a", "b", "a"], "x": [1.0, None, None, None]})
    out = nb.missing_profile(df, "x", "g")
    assert list(out.index) == ["a", "b"]                              # bằng số dòng: khoá tăng dần
    assert out["rows"].tolist() == [2, 2] and out["missing"].tolist() == [2, 1]
    assert str(out["rows"].dtype).startswith("int") and str(out["missing"].dtype).startswith("int")


def test_invoice_summary(nb):
    out = nb.invoice_summary(lines())
    assert list(out.columns) == ["lines", "revenue", "missing", "mixed", "country", "hour"]
    assert out.index.name == "Invoice"
    assert list(out.index) == ["1", "2", "3", "4", "5"]
    assert out["lines"].tolist() == [2, 3, 1, 2, 1]
    assert out["revenue"].tolist() == pytest.approx([7.0, 10.0, 5.0, 8.0, 4.0])
    assert out["missing"].tolist() == [False, True, False, False, False]
    assert out["mixed"].tolist() == [False, False, False, True, False]
    assert out["country"].tolist() == ["UK", "UK", "France", "UK", "France"]
    assert out["hour"].tolist() == [9, 16, 11, 17, 10]                # giờ của dòng sớm nhất


def test_invoice_summary_does_not_mutate_input(nb):
    df = lines()
    before = df.copy()
    nb.invoice_summary(df)
    nb.missing_profile(df, "Customer ID", "Country")
    pd.testing.assert_frame_equal(df, before)


def read_sheet(sheet: str) -> pd.DataFrame:
    """Sheet gốc (Invoice, StockCode, Description là chuỗi), cache parquet trong thư mục tạm: xlsx đọc mất 30-60 giây."""
    src = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    st = src.stat()
    cache = Path(tempfile.gettempdir()) / "da-cache" / f"online_retail_II-{sheet.replace(' ', '_')}-{st.st_size}-{st.st_mtime_ns}.parquet"
    if not cache.exists():
        df = pd.read_excel(src, sheet_name=sheet, dtype={"Invoice": str, "StockCode": str, "Description": str})
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
        df.to_parquet(tmp, index=False)
        os.replace(tmp, cache)
    return pd.read_parquet(cache)


@pytest.fixture(scope="module")
def valid():
    tx = read_sheet("Year 2010-2011")
    keep = ~tx["Invoice"].astype(str).str.startswith("C") & (tx["Quantity"] > 0) & (tx["Price"] > 0)
    return tx[keep]                                                    # dòng hợp lệ theo định nghĩa dùng chung


def test_real_missing_profile(nb, valid):
    out = nb.missing_profile(valid, "Customer ID", "Country")
    assert out.index[0] == "United Kingdom"
    assert out.loc["United Kingdom", "rows"] == 485_123
    assert out.loc["United Kingdom", "missing_rate"] == pytest.approx(0.2696, abs=1e-4)
    assert out["missing"].sum() == 132_220


def test_real_invoice_summary(nb, valid):
    inv = nb.invoice_summary(valid)
    assert len(inv) == 19_960
    assert inv["mixed"].sum() == 0
    assert inv["missing"].sum() == 1_428
    assert inv.loc[inv["missing"], "revenue"].sum() == pytest.approx(1_755_276.64, abs=0.01)
    assert inv.groupby("missing")["lines"].median().tolist() == [15.0, 36.0]


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 250 <= words <= 700, f"Memo một trang: 250-700 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"
