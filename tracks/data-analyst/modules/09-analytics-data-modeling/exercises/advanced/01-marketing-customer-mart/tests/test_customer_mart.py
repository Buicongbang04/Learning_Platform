"""Chấm customer_mart.sql (trên dữ liệu nhỏ sinh trong test và dữ liệu thật) và khung DESIGN.md."""
import os
import re
import tempfile
import uuid
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
REQUIRED = ["customer_id", "first_purchase_date", "cohort_month", "last_purchase_date", "recency_days", "orders",
            "revenue", "aov", "active_months", "main_country", "is_winback_target"]
HEADINGS = ["## Câu hỏi của Marketing", "## Grain và bảng", "## Định nghĩa cột", "## Data test",
            "## Quyết định và giới hạn", "## Kết quả trên dữ liệu thật"]


def build(fct: pd.DataFrame, snapshot: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.register("src", fct)
    con.execute("CREATE TABLE fct_sales_line AS SELECT * FROM src")
    con.unregister("src")
    con.execute(f"CREATE TABLE params AS SELECT DATE '{snapshot}' AS snapshot_date")
    con.execute(ex.read("customer_mart.sql"))
    return con


def small_fct() -> pd.DataFrame:
    nan = np.nan
    rows = [
        (1, "1", "2011-01-10 10:00", 1, "United Kingdom", 10.0),
        (2, "1", "2011-01-10 10:00", 1, "United Kingdom", 5.0),
        (3, "2", "2011-02-15 09:00", 1, "United Kingdom", 20.0),
        (4, "3", "2011-03-01 11:00", 2, "France", 50.0),
        (5, "4", "2011-05-20 12:00", 2, "Germany", 30.0),
        (6, "5", "2011-05-20 15:00", 2, "France", 10.0),
        (7, "6", "2011-01-05 08:00", 3, "United Kingdom", 100.0),
        (8, "7", "2011-07-01 08:00", 4, "United Kingdom", 40.0),   # sau ngày chốt: không tính
        (9, "8", "2011-06-01 00:00", 2, "France", 999.0),          # đúng ngày chốt: không tính (kỳ nửa mở)
        (10, "9", "2011-02-01 10:00", nan, "United Kingdom", 70.0),  # khách vãng lai
        (11, "10", "2011-03-02 10:00", 5, "Spain", 15.0),
        (12, "11", "2011-03-03 10:00", 5, "Spain", 15.0),
        (13, "12", "2011-04-01 10:00", 6, "Belgium", 10.0),
        (14, "13", "2011-04-02 10:00", 6, "Austria", 10.0),
    ]
    df = pd.DataFrame(rows, columns=["line_id", "invoice_no", "invoiced_at", "customer_id", "country", "revenue"])
    df["invoiced_at"] = pd.to_datetime(df["invoiced_at"])
    df["customer_id"] = df["customer_id"].astype("Int64")
    return df


@pytest.fixture(scope="module")
def small():
    return build(small_fct(), "2011-06-01").execute("SELECT * FROM mart_customer ORDER BY customer_id").df()


def test_columns_and_grain(small):
    missing = [c for c in REQUIRED if c not in small.columns]
    assert not missing, f"Thiếu cột: {missing}"
    assert small.customer_id.tolist() == [1, 2, 3, 5, 6], "Một dòng mỗi khách có mã, chỉ tính giao dịch trước ngày chốt"


def test_values(small):
    s = small.set_index("customer_id")
    assert s["orders"].tolist() == [2, 3, 1, 2, 2]
    assert s["revenue"].tolist() == pytest.approx([35.0, 90.0, 100.0, 30.0, 20.0])
    assert s["aov"].tolist() == pytest.approx([17.5, 30.0, 100.0, 15.0, 10.0])
    assert s["recency_days"].tolist() == [106, 12, 147, 90, 60]
    assert s["active_months"].tolist() == [2, 2, 1, 1, 1]
    assert [str(pd.Timestamp(d).date()) for d in s["first_purchase_date"]] == \
        ["2011-01-10", "2011-03-01", "2011-01-05", "2011-03-02", "2011-04-01"]
    assert [str(pd.Timestamp(d).date()) for d in s["cohort_month"]] == \
        ["2011-01-01", "2011-03-01", "2011-01-01", "2011-03-01", "2011-04-01"]
    assert [str(pd.Timestamp(d).date()) for d in s["last_purchase_date"]] == \
        ["2011-02-15", "2011-05-20", "2011-01-05", "2011-03-03", "2011-04-02"]
    assert s["main_country"].tolist() == ["United Kingdom", "France", "United Kingdom", "Spain", "Austria"]
    assert s["is_winback_target"].tolist() == [True, False, False, False, False]


def test_snapshot_is_a_parameter():
    later = build(small_fct(), "2011-07-15").execute("SELECT * FROM mart_customer ORDER BY customer_id").df()
    s = later.set_index("customer_id")
    assert 4 in s.index and s.loc[2, "orders"] == 4 and s.loc[2, "revenue"] == pytest.approx(1089.0)
    assert s.loc[5, "is_winback_target"], "Ngày chốt muộn hơn: khách 5 thành mục tiêu win-back"


def test_rerunnable():
    con = build(small_fct(), "2011-06-01")
    con.execute(ex.read("customer_mart.sql"))
    assert con.execute("SELECT count(*) FROM mart_customer").fetchall()[0][0] == 5


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


def test_real_data_reconciles():
    raw = load_retail_2010_2011()
    keep = ~raw.Invoice.str.startswith("C") & (raw.Quantity > 0) & (raw.Price > 0)
    v = raw[keep]
    fct = pd.DataFrame({"line_id": v.source_row, "invoice_no": v.Invoice, "invoiced_at": v.InvoiceDate,
                        "customer_id": v["Customer ID"].astype("Int64"), "country": v.Country,
                        "revenue": v.Quantity * v.Price})
    mart = build(fct, "2011-12-01").execute("SELECT * FROM mart_customer").df()
    before = fct[(fct.invoiced_at < "2011-12-01") & fct.customer_id.notna()]
    assert mart.customer_id.is_unique and len(mart) == before.customer_id.nunique()
    assert mart.revenue.sum() == pytest.approx(before.revenue.sum(), abs=0.01)
    assert mart.orders.sum() == before.invoice_no.nunique()


def test_design_doc():
    doc = ex.read("DESIGN.md")
    assert "TODO" not in doc, "Còn TODO trong DESIGN.md"
    words = len(doc.split())
    assert 300 <= words <= 1500, f"DESIGN.md 300-1500 từ, hiện có {words}"
    for heading in HEADINGS:
        assert heading in doc, f"Thiếu mục {heading}"
    results = doc.split("## Kết quả trên dữ liệu thật", 1)[1]
    assert len(re.findall(r"\d", results)) >= 5, "Mục kết quả cần số liệu thật từ mart"
