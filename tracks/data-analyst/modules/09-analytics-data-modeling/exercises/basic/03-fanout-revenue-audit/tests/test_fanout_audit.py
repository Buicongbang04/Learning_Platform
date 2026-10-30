import os
import tempfile
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("fanout_audit.ipynb")


def load_retail_2010_2011() -> pd.DataFrame:
    """Bản chép của loader chuẩn (basic/02-retail-star-schema/tests): sheet Year 2010-2011 + source_row, cache parquet."""
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    st = xlsx.stat()
    cache = Path(tempfile.gettempdir()) / "da-cache" / f"m09_2010-2011_{st.st_mtime_ns}_{st.st_size}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    df = pd.read_excel(xlsx, sheet_name="Year 2010-2011")
    df.insert(0, "source_row", range(1, len(df) + 1))
    for col in ["Invoice", "StockCode", "Description", "Country"]:
        df[col] = df[col].map(lambda x: None if pd.isna(x) else str(x))
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(f".{uuid.uuid4().hex}.tmp")
    df.to_parquet(tmp)
    os.replace(tmp, cache)
    return df


def small_lines():
    nan = np.nan
    return pd.DataFrame({
        "source_row": [1, 2, 3, 4, 5, 6],
        "Invoice": ["A1", "A1", "A1", "A2", "A3", "A3"],
        "StockCode": ["X", "X", "Y", "X", "Z", "Y"],
        "Description": ["RED", "RED", "BLUE", "RED", "GREEN", "BLUE"],
        "Quantity": [1, 1, 2, 5, 1, 3],
        "Price": [2.0, 2.0, 3.0, 1.0, 10.0, 3.0],
        "InvoiceDate": pd.to_datetime(["2011-01-01 10:01", "2011-01-01 10:00", "2011-01-01 10:01",
                                       "2011-01-02 09:00", "2011-01-03 12:00", "2011-01-03 12:00"]),
        "Customer ID": [7.0, 7.0, 7.0, nan, 8.0, 8.0],
        "Country": ["United Kingdom", "United Kingdom", "United Kingdom", "France", "Spain", "Spain"],
    }).assign(revenue=lambda d: d.Quantity * d.Price)


def test_key_profile(nb):
    lines = small_lines()
    assert nb.key_profile(lines, ["source_row"]) == {
        "rows": 6, "distinct_keys": 6, "duplicated_keys": 0, "max_rows_per_key": 1, "is_unique": True}
    assert nb.key_profile(lines, ["Invoice", "StockCode"]) == {
        "rows": 6, "distinct_keys": 5, "duplicated_keys": 1, "max_rows_per_key": 2, "is_unique": False}
    out = nb.key_profile(lines, ["Invoice"])
    assert out["duplicated_keys"] == 2 and out["max_rows_per_key"] == 3
    assert all(type(out[k]) is int for k in ["rows", "distinct_keys", "duplicated_keys", "max_rows_per_key"])
    assert type(out["is_unique"]) is bool


def test_key_profile_counts_missing_as_a_key(nb):
    df = pd.DataFrame({"k": [1.0, np.nan, np.nan]})
    assert nb.key_profile(df, ["k"])["duplicated_keys"] == 1


def test_join_inflation_fanout(nb):
    lines = small_lines()
    dim = pd.DataFrame({"StockCode": ["X", "X", "Y", "Z"], "Description": ["RED", "RED MUG", "BLUE", "GREEN"]})
    out = nb.join_inflation(lines, dim, "StockCode", "revenue")
    # X có 3 dòng (2 + 2 + 5 = 9 GBP) bị nhân đôi; tổng 34 GBP
    assert out["rows_before"] == 6 and out["rows_after"] == 9
    assert out["before"] == pytest.approx(34.0) and out["after"] == pytest.approx(43.0)
    assert out["inflation"] == pytest.approx(9 / 34)


def test_join_inflation_many_to_one_is_zero(nb):
    lines = small_lines()
    dim = pd.DataFrame({"StockCode": ["X", "Y", "Z"], "revenue": [0.0, 0.0, 0.0]})   # trùng tên cột với left
    out = nb.join_inflation(lines, dim, "StockCode", "revenue")
    assert out["rows_after"] == 6 and out["inflation"] == pytest.approx(0.0)
    assert out["after"] == pytest.approx(34.0), "measure là cột của left, không phải cột cùng tên của right"


def test_join_inflation_does_not_mutate(nb):
    lines, dim = small_lines(), pd.DataFrame({"StockCode": ["X"], "d": [1]})
    before = lines.copy()
    nb.join_inflation(lines, dim, "StockCode", "revenue")
    pd.testing.assert_frame_equal(lines, before)


def test_invoice_header(nb):
    out = nb.invoice_header(small_lines())
    assert list(out.columns) == ["Invoice", "Customer ID", "Country", "invoiced_at", "n_lines", "invoice_total"]
    assert list(out.index) == [0, 1, 2]
    assert out.Invoice.tolist() == ["A1", "A2", "A3"]
    assert out.n_lines.tolist() == [3, 1, 2]
    assert out.invoice_total.tolist() == pytest.approx([10.0, 5.0, 19.0])
    assert out.invoiced_at.tolist() == list(pd.to_datetime(["2011-01-01 10:00", "2011-01-02 09:00", "2011-01-03 12:00"]))
    assert pd.isna(out.loc[1, "Customer ID"]) and out.loc[1, "Country"] == "France"


def test_aov(nb):
    lines = small_lines()
    assert nb.aov(lines) == pytest.approx(34.0 / 3)   # 34 GBP / 3 hoá đơn, không phải 34 / 6 dòng
    assert isinstance(nb.aov(lines), float)


@pytest.fixture(scope="module")
def real_lines(nb):
    return nb.valid_lines(load_retail_2010_2011())


def test_real_keys_and_fanout(nb, real_lines):
    pair = nb.key_profile(real_lines, ["Invoice", "StockCode"])
    assert pair["rows"] == 530_105 and pair["distinct_keys"] == 519_603
    assert pair["duplicated_keys"] == 9_566 and pair["max_rows_per_key"] == 20
    naive = real_lines[["StockCode", "Description"]].drop_duplicates()
    assert nb.key_profile(naive, ["StockCode"])["duplicated_keys"] == 220
    res = nb.join_inflation(real_lines, naive, "StockCode", "revenue")
    assert res["rows_after"] == 584_319
    assert res["before"] == pytest.approx(10_666_702.54, abs=0.01)
    assert res["inflation"] == pytest.approx(0.1227, abs=0.0001)


def test_real_header_and_aov(nb, real_lines):
    header = nb.invoice_header(real_lines)
    assert len(header) == 19_960
    assert header.invoice_total.sum() == pytest.approx(10_666_702.54, abs=0.01)
    assert header.n_lines.max() == 1_114
    assert nb.aov(real_lines) == pytest.approx(534.40, abs=0.01)
    res = nb.join_inflation(header, real_lines[["Invoice", "StockCode"]], "Invoice", "invoice_total")
    assert res["after"] / res["before"] == pytest.approx(68.25, abs=0.01)
