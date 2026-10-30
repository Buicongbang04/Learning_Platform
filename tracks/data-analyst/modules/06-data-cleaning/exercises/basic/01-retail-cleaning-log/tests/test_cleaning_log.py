import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
REASONS = ["cancelled", "non_positive_quantity", "non_positive_price", "fee_code", "exact_duplicate"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("cleaning_log.ipynb")


def frame(rows):
    out = pd.DataFrame(rows, columns=["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price",
                                      "Customer ID", "Country"])
    out["InvoiceDate"] = pd.to_datetime(out["InvoiceDate"])
    return out


def small_tx():
    nan = np.nan
    return frame([
        (489434, "85048", "15CM CHRISTMAS GLASS BALL ", 12, "2009-12-01 07:45", 6.95, 13085.0, "United Kingdom"),  # 0 giữ
        ("C489449", "22087", "PAPER BUNTING", -12, "2009-12-01 10:33", 2.95, 16321.0, "Australia"),         # 1 cancelled
        (489435, "22087", "PAPER  BUNTING", 0, "2009-12-01 07:46", 2.95, nan, "United Kingdom"),            # 2 quantity
        (489436, "21523", "DOORMAT", 5, "2009-12-01 09:06", 0.0, 13078.0, "United Kingdom"),               # 3 price
        ("A506401", "B", "Adjust bad debt", 1, "2010-04-29 13:36", -53594.36, nan, "United Kingdom"),     # 4 price (trước fee)
        (489437, "post", "POSTAGE", 1, "2009-12-01 09:08", 18.0, 12682.0, "France"),                       # 5 fee_code (chữ thường)
        (489437, "m", "Manual", 1, "2009-12-01 09:08", 4.25, 12682.0, "France"),                           # 6 fee_code
        (489438, "85123a", "WHITE HANGING HEART T-LIGHT HOLDER", 6, "2009-12-01 09:24", 2.55, nan, "United Kingdom"),  # 7 giữ
        (489438, "85123A", " WHITE HANGING HEART T-LIGHT HOLDER", 6, "2009-12-01 09:24", 2.55, nan, "United Kingdom"),  # 8 trùng 7 sau chuẩn hoá
        (489439, "21232", "STRAWBERRY CERAMIC TRINKET BOX", 3, "2009-12-01 09:28", 1.25, 13085.0, "United Kingdom"),  # 9 giữ
        (489439, "21232", "STRAWBERRY CERAMIC TRINKET BOX", 3, "2009-12-01 09:28", 1.25, 13085.0, "United Kingdom"),  # 10 trùng 9
        ("C489440", "POST", "POSTAGE", -1, "2009-12-01 09:30", 18.0, 12682.0, "France"),                   # 11 cancelled (lý do đầu tiên)
    ])


def test_normalize_types_and_text(nb):
    out = nb.normalize(small_tx())
    assert out["Invoice"].tolist()[:2] == ["489434", "C489449"]
    assert out.loc[5, "StockCode"] == "POST" and out.loc[7, "StockCode"] == "85123A"
    assert out.loc[0, "Description"] == "15CM CHRISTMAS GLASS BALL"
    assert out.loc[2, "Description"] == "PAPER BUNTING"                      # gộp khoảng trắng thừa
    assert out.loc[8, "Description"] == "WHITE HANGING HEART T-LIGHT HOLDER"
    assert str(out["Customer ID"].dtype) == "Int64"                           # mã khách là số nguyên, thiếu là <NA>
    assert out["Customer ID"].isna().sum() == 4
    assert out.loc[0, "Customer ID"] == 13085
    assert len(out) == 12 and list(out.index) == list(range(12))


def test_normalize_does_not_mutate_input(nb):
    tx = small_tx()
    before = tx.copy()
    nb.normalize(tx)
    pd.testing.assert_frame_equal(tx, before)


def test_clean_with_log_rows(nb):
    clean, log = nb.clean_with_log(small_tx())
    assert sorted(clean.index) == [0, 7, 9]
    assert clean["StockCode"].tolist() == ["85048", "85123A", "21232"]
    assert clean["Customer ID"].isna().sum() == 1                              # thiếu mã khách không phải lý do loại


def test_clean_with_log_log_table(nb):
    clean, log = nb.clean_with_log(small_tx())
    assert list(log.columns) == ["reason", "rows_removed", "rows_left", "revenue_removed"]
    assert log["reason"].tolist() == REASONS
    assert log["rows_removed"].tolist() == [2, 1, 2, 2, 2]
    assert log["rows_left"].tolist() == [10, 9, 7, 5, 3]
    assert log["rows_left"].iloc[-1] == len(clean)
    assert log["revenue_removed"].tolist() == pytest.approx([-35.4 - 18.0, 0.0, -53594.36, 22.25, 15.3 + 3.75])


def test_clean_with_log_reconciles(nb):
    tx = small_tx()
    clean, log = nb.clean_with_log(tx)
    raw = (tx["Quantity"] * tx["Price"]).sum()
    kept = (clean["Quantity"] * clean["Price"]).sum()
    assert raw - log["revenue_removed"].sum() == pytest.approx(kept)


def test_clean_with_log_does_not_mutate_input(nb):
    tx = small_tx()
    before = tx.copy()
    nb.clean_with_log(tx)
    pd.testing.assert_frame_equal(tx, before)


def test_missing_report(nb):
    df = pd.DataFrame({"a": [1, None, None, 4], "b": ["x", "y", None, "z"], "c": [1, 2, 3, 4]})
    out = nb.missing_report(df)
    assert list(out.columns) == ["missing", "missing_share"]
    assert list(out.index) == ["a", "b", "c"]
    assert out["missing"].tolist() == [2, 1, 0]
    assert out["missing_share"].tolist() == pytest.approx([0.5, 0.25, 0.0])


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
def real_tx():
    return read_sheet("Year 2009-2010")


def test_real_cleaning_log(nb, real_tx):
    clean, log = nb.clean_with_log(real_tx)
    assert log["rows_removed"].tolist() == [10_206, 2_121, 1_569, 2_273, 6_830]
    assert len(clean) == 502_462
    assert log["revenue_removed"].tolist() == pytest.approx([-629_855.37, 0.0, -136_552.02, 466_073.72, 34_100.71], abs=0.01)
    assert (clean["Quantity"] * clean["Price"]).sum() == pytest.approx(9_805_717.59, abs=0.01)
    miss = nb.missing_report(clean)
    assert miss.index[0] == "Customer ID"
    assert miss.loc["Customer ID", "missing"] == 102_908
