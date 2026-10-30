import os
import tempfile
import uuid
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
NAMES = ["revenue", "orders", "active_customers", "new_customers", "aov"]


@pytest.fixture(scope="module")
def layer():
    return ex.module("metric_layer.py")


@pytest.fixture(scope="module")
def reports():
    return ex.module("reports.py")


def load_defs() -> dict:
    """Đọc metrics.yml qua metric_layer; định nghĩa sai thì test FAIL với thông báo của metric layer."""
    try:
        return ex.module("metric_layer.py").load_metrics(ex.path("metrics.yml"))
    except ValueError as exc:
        pytest.fail(f"metrics.yml không hợp lệ: {exc}")


def fct_from_lines(lines: pd.DataFrame) -> duckdb.DuckDBPyConnection:
    """lines: Invoice, InvoiceDate, Country, Customer ID, revenue (đã là dòng hợp lệ) -> bảng fct_sales."""
    con = duckdb.connect()
    con.register("src", lines)
    con.execute("""
        CREATE TABLE fct_sales AS
        WITH base AS (
            SELECT row_number() OVER () AS line_id, CAST(Invoice AS VARCHAR) AS invoice_no,
                   CAST(date_trunc('month', InvoiceDate) AS DATE) AS invoice_month, Country AS country,
                   CAST("Customer ID" AS BIGINT) AS customer_id, revenue
            FROM src
        )
        SELECT b.*, f.first_purchase_month
        FROM base b
        LEFT JOIN (SELECT customer_id, min(invoice_month) AS first_purchase_month
                   FROM base WHERE customer_id IS NOT NULL GROUP BY 1) f USING (customer_id)
    """)
    con.unregister("src")
    return con


def small_lines():
    nan = np.nan
    return pd.DataFrame({
        "Invoice": ["1", "1", "2", "3", "4", "5", "6", "7"],
        "InvoiceDate": pd.to_datetime(["2011-01-03", "2011-01-03", "2011-01-10", "2011-01-12",
                                       "2011-02-01", "2011-02-07", "2011-02-20", "2011-01-25"]),
        "Country": ["United Kingdom", "United Kingdom", "France", "United Kingdom", "United Kingdom", "France", "France",
                    "United Kingdom"],
        "Customer ID": [1.0, 1.0, 2.0, nan, 1.0, 3.0, 2.0, nan],
        "revenue": [10.0, 5.0, 40.0, 6.0, 20.0, 9.0, 30.0, 2.0],
    })


@pytest.fixture(scope="module")
def small():
    return fct_from_lines(small_lines())


def test_definitions_documented():
    metrics = load_defs()
    assert set(NAMES) <= set(metrics), f"Thiếu metric: {sorted(set(NAMES) - set(metrics))}"
    for name in NAMES:
        m = metrics[name]
        assert "TODO" not in str(m), f"{name}: còn TODO"
        assert len(m["description"].strip()) >= 30, f"{name}: mô tả cần đủ để người không biết SQL hiểu (>= 30 ký tự)"
        assert m["owner"].strip(), f"{name}: cần owner"
    assert metrics["new_customers"]["caveats"], "new_customers: ghi lưu ý về tháng đầu của dữ liệu"
    assert metrics["active_customers"]["caveats"] and metrics["aov"]["caveats"]


def test_definitions_semantics():
    metrics = load_defs()
    assert {n: metrics[n]["additive_over_time"] for n in NAMES} == {
        "revenue": True, "orders": True, "active_customers": False, "new_customers": True, "aov": False}
    assert metrics["orders"]["type"] == "count_distinct" and metrics["orders"]["expr"].strip() == "invoice_no"
    assert metrics["active_customers"]["type"] == "count_distinct"
    aov = metrics["aov"]
    assert aov["type"] == "ratio" and (aov["numerator"], aov["denominator"]) == ("revenue", "orders"), \
        "aov là tỉ số của tổng (revenue / orders), không phải trung bình"


def test_layer_on_small(layer, small):
    metrics = load_defs()
    total = layer.query(small, metrics, NAMES).iloc[0]
    assert total["revenue"] == pytest.approx(122.0)
    assert total["orders"] == 7 and total["active_customers"] == 3 and total["new_customers"] == 3
    assert total["aov"] == pytest.approx(122 / 7)
    by_month = layer.query(small, metrics, NAMES, by=["month"])
    assert by_month["month"].tolist() == ["2011-01", "2011-02"]
    assert by_month["active_customers"].tolist() == [2, 3]          # cộng ra 5 > 3 khách thật
    assert by_month["new_customers"].tolist() == [2, 1]
    assert by_month["aov"].tolist() == pytest.approx([63 / 4, 59 / 3])


def test_finance_monthly(reports, small):
    metrics = load_defs()
    out = reports.finance_monthly(small, metrics)
    assert list(out.columns) == ["month", "revenue", "orders", "aov"]
    assert out["month"].tolist() == ["2011-01", "2011-02", "Tổng"]
    assert out["revenue"].tolist() == pytest.approx([63.0, 59.0, 122.0])
    assert out["orders"].tolist() == [4, 3, 7]   # hoá đơn 1 có 2 dòng nhưng là một đơn
    assert out["aov"].tolist() == pytest.approx([63 / 4, 59 / 3, 122 / 7])
    assert out["aov"].iloc[-1] != pytest.approx(out["aov"].iloc[:-1].mean()), \
        "Dòng Tổng: revenue / orders cả kỳ, không lấy trung bình các tháng"


def test_marketing_country(reports, small):
    metrics = load_defs()
    out = reports.marketing_country(small, metrics)
    assert list(out.columns) == ["country", "revenue", "orders", "active_customers", "new_customers", "aov"]
    assert out["country"].tolist() == ["France", "United Kingdom", "Tổng"]
    assert out["revenue"].tolist() == pytest.approx([79.0, 43.0, 122.0])
    assert out["orders"].tolist() == [3, 4, 7]
    assert out["active_customers"].tolist() == [2, 1, 3]
    assert out["new_customers"].tolist() == [2, 1, 3]
    assert out["aov"].tolist() == pytest.approx([79 / 3, 43 / 4, 122 / 7])


def test_two_reports_agree(reports, small):
    metrics = load_defs()
    fin = reports.finance_monthly(small, metrics).set_index("month").loc["Tổng"]
    mkt = reports.marketing_country(small, metrics).set_index("country").loc["Tổng"]
    for col in ["revenue", "orders", "aov"]:
        assert fin[col] == pytest.approx(mkt[col]), f"Hai báo cáo lệch nhau ở dòng Tổng, cột {col}"


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


@pytest.fixture(scope="module")
def real():
    raw = load_retail_2010_2011()
    keep = ~raw.Invoice.str.startswith("C") & (raw.Quantity > 0) & (raw.Price > 0)
    return fct_from_lines(raw[keep].assign(revenue=lambda d: d.Quantity * d.Price))


def test_real_reports(reports, real):
    metrics = load_defs()
    fin = reports.finance_monthly(real, metrics).set_index("month")
    assert fin.loc["2011-11", "revenue"] == pytest.approx(1_509_496.33, abs=0.01)
    assert fin.loc["2011-11", "orders"] == 2_769 and fin.loc["2011-11", "aov"] == pytest.approx(545.14, abs=0.01)
    assert fin.loc["Tổng", "revenue"] == pytest.approx(10_666_702.54, abs=0.01)
    assert fin.loc["Tổng", "orders"] == 19_960 and fin.loc["Tổng", "aov"] == pytest.approx(534.40, abs=0.01)
    mkt = reports.marketing_country(real, metrics).set_index("country")
    assert mkt.index[0] == "United Kingdom" and mkt.index[-1] == "Tổng" and len(mkt) == 39
    assert mkt.loc["United Kingdom", "revenue"] == pytest.approx(9_025_222.08, abs=0.01)
    assert mkt.loc["United Kingdom", "active_customers"] == 3_920
    assert mkt.loc["Tổng", "active_customers"] == 4_338 and mkt.loc["Tổng", "new_customers"] == 4_338
    assert mkt.drop("Tổng")["active_customers"].sum() == 4_346      # cộng các dòng: 8 khách bị đếm hai lần
    for col in ["revenue", "orders", "aov"]:
        assert fin.loc["Tổng", col] == pytest.approx(mkt.loc["Tổng", col])
