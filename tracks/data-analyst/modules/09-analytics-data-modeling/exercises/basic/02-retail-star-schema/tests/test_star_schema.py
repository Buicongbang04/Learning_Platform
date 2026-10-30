"""Chạy starter/star_schema.sql trên DuckDB: dữ liệu nhỏ sinh trong test và sheet Year 2010-2011 thật."""
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
COLUMNS = ["source_row", "Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]
TABLES = {
    "dim_date": ["date_key", "full_date", "year", "month", "month_start", "day_of_week", "is_weekend"],
    "dim_product": ["product_key", "stock_code", "description", "is_merchandise"],
    "dim_customer": ["customer_key", "customer_id", "current_country", "first_purchase_date"],
    "fct_sales_line": ["line_key", "invoice_no", "date_key", "customer_key", "product_key", "country",
                       "quantity", "unit_price", "revenue"],
}


def load_retail_2010_2011() -> pd.DataFrame:
    """Sheet Year 2010-2011 nguyên trạng + source_row. Đọc xlsx lần đầu 30-60 giây, sau đó đọc cache parquet
    trong thư mục tạm (khoá theo mtime + cỡ tệp, ghi nguyên tử). Bản chuẩn của loader trong module 09: các bài
    khác chép y hệt."""
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    st = xlsx.stat()
    cache = Path(tempfile.gettempdir()) / "da-cache" / f"m09_2010-2011_{st.st_mtime_ns}_{st.st_size}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    df = pd.read_excel(xlsx, sheet_name="Year 2010-2011")
    df.insert(0, "source_row", range(1, len(df) + 1))
    for col in ["Invoice", "StockCode", "Description", "Country"]:
        df[col] = df[col].map(lambda x: None if pd.isna(x) else str(x))  # xlsx trộn int và str
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(f".{uuid.uuid4().hex}.tmp")
    df.to_parquet(tmp)
    os.replace(tmp, cache)
    return df


def raw_fixture() -> pd.DataFrame:
    nan = np.nan
    rows = [
        (1, "1001", "10001", "RED MUG", 2, "2011-01-03 10:00", 1.5, 1.0, "United Kingdom"),
        (2, "1001", "10001", "RED MUG", 1, "2011-01-03 10:00", 1.5, 1.0, "United Kingdom"),   # cùng hoá đơn, cùng mã: dòng thật
        (3, "1002", "10001", "MUG RED", 3, "2011-01-04 11:00", 1.4, 2.0, "France"),
        (4, "1003", "20002", "BLUE BOWL", 1, "2011-01-04 12:00", 5.0, nan, "United Kingdom"),  # khách vãng lai
        (5, "1004", "20002", "BOWL BLUE", 1, "2011-01-05 09:00", 5.0, 3.0, "Germany"),         # hoà 1-1: lấy BLUE BOWL
        (6, "C1005", "10001", "RED MUG", -1, "2011-01-05 10:00", 1.5, 1.0, "United Kingdom"),  # huỷ
        (7, "1006", "30003", "GREEN VASE", 4, "2011-01-06 10:00", 0.0, 1.0, "United Kingdom"), # giá 0
        (8, "1007", "POST", "POSTAGE", 1, "2011-01-06 15:00", 18.0, 2.0, "France"),           # phí, không phải hàng
        (9, "1008", "10001", "RED MUG", 5, "2011-01-07 08:00", 1.2, 2.0, "Belgium"),           # khách 2 đổi quốc gia
        (10, "1009", "85123A", "WHITE HEART", 1, "2011-01-09 16:00", 2.55, 1.0, "United Kingdom"),
        (11, "1010", "20002", "BLUE BOWL", -2, "2011-01-09 17:00", 5.0, 3.0, "Germany"),       # số lượng âm
    ]
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df


def build(raw: pd.DataFrame, runs: int = 1) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.register("src", raw)
    con.execute("CREATE TABLE raw_sales_lines AS SELECT * FROM src")
    con.unregister("src")
    sql = ex.read("star_schema.sql")
    for _ in range(runs):
        con.execute(sql)
    return con


def rows(con, sql):
    return con.execute(sql).fetchall()


@pytest.fixture(scope="module")
def small():
    return build(raw_fixture(), runs=2)  # chạy hai lần: tệp phải chạy lại được (CREATE OR REPLACE)


def test_tables_and_columns(small):
    for table, cols in TABLES.items():
        got = [r[0] for r in rows(small, f"DESCRIBE {table}")]
        assert got == cols, f"{table}: cần cột {cols}, đang có {got}"
    assert rows(small, "SELECT count(*) FROM raw_sales_lines") == [(11,)], "Không được sửa bảng nguồn"
    for table in TABLES:
        assert rows(small, f"SELECT count(*) FROM {table}")[0][0] > 0, f"{table} đang rỗng"


def test_fact_grain_and_filter(small):
    got = rows(small, "SELECT line_key FROM fct_sales_line ORDER BY line_key")
    assert [r[0] for r in got] == [1, 2, 3, 4, 5, 8, 9, 10], "Fact giữ đúng các dòng hợp lệ, kể cả 2 dòng cùng hoá đơn + mã"
    assert rows(small, "SELECT round(sum(revenue), 2) FROM fct_sales_line") == [(45.25,)]
    assert rows(small, "SELECT revenue FROM fct_sales_line WHERE line_key = 3") == [(pytest.approx(4.2),)]


def test_dim_product_one_row_per_code(small):
    got = rows(small, "SELECT product_key, stock_code, description, is_merchandise FROM dim_product ORDER BY product_key")
    assert got == [
        (1, "10001", "RED MUG", True),        # RED MUG 3 dòng hợp lệ, MUG RED 1 dòng
        (2, "20002", "BLUE BOWL", True),      # hoà 1-1: mô tả nhỏ nhất theo chữ cái
        (3, "85123A", "WHITE HEART", True),   # 5 chữ số + chữ cái vẫn là hàng hoá
        (4, "POST", "POSTAGE", False),
    ]


def test_dim_customer_unknown_member_and_scd1(small):
    got = rows(small, """SELECT customer_key, customer_id, current_country, CAST(first_purchase_date AS VARCHAR)
                         FROM dim_customer ORDER BY customer_key""")
    assert got == [
        (0, None, "Unknown", None),
        (1, 1, "United Kingdom", "2011-01-03"),
        (2, 2, "Belgium", "2011-01-04"),      # quốc gia của dòng hợp lệ muộn nhất
        (3, 3, "Germany", "2011-01-05"),
    ]


def test_fact_keys(small):
    got = rows(small, "SELECT line_key, date_key, customer_key, product_key, country FROM fct_sales_line ORDER BY line_key")
    assert got == [
        (1, 20110103, 1, 1, "United Kingdom"),
        (2, 20110103, 1, 1, "United Kingdom"),
        (3, 20110104, 2, 1, "France"),        # quốc gia của hoá đơn, không phải current_country
        (4, 20110104, 0, 2, "United Kingdom"),
        (5, 20110105, 3, 2, "Germany"),
        (8, 20110106, 2, 4, "France"),
        (9, 20110107, 2, 1, "Belgium"),
        (10, 20110109, 1, 3, "United Kingdom"),
    ]
    # dim_date là mẫu có sẵn: liên tục từ ngày bán đầu tới ngày bán cuối, kể cả ngày không có đơn
    dates = rows(small, "SELECT date_key, day_of_week, is_weekend FROM dim_date ORDER BY date_key")
    assert [r[0] for r in dates] == list(range(20110103, 20110110))
    assert dates[5] == (20110108, 6, True) and dates[0] == (20110103, 1, False)


def check_integrity(con):
    assert rows(con, "SELECT count(*) FROM fct_sales_line")[0][0] > 0, "fct_sales_line đang rỗng"
    for dim, key in [("dim_date", "date_key"), ("dim_product", "product_key"), ("dim_customer", "customer_key")]:
        dup = rows(con, f"SELECT count(*) FROM (SELECT {key} FROM {dim} GROUP BY 1 HAVING count(*) > 1)")[0][0]
        assert dup == 0, f"{dim}.{key} phải unique"
        orphan = rows(con, f"SELECT count(*) FROM fct_sales_line f LEFT JOIN {dim} d USING ({key}) WHERE d.{key} IS NULL")[0][0]
        assert orphan == 0, f"{orphan} dòng fact có {key} không có trong {dim}"
    joined, fact = rows(con, """SELECT (SELECT sum(revenue) FROM fct_sales_line f JOIN dim_product USING (product_key)
                                          JOIN dim_customer USING (customer_key) JOIN dim_date USING (date_key)),
                                       (SELECT sum(revenue) FROM fct_sales_line)""")[0]
    assert joined == pytest.approx(fact), "Join fact với cả ba dimension phải giữ nguyên tổng doanh thu (không fan-out)"
    assert rows(con, "SELECT count(*) FROM fct_sales_line WHERE customer_key IS NULL OR product_key IS NULL")[0][0] == 0


def test_integrity_small(small):
    check_integrity(small)


@pytest.fixture(scope="module")
def real():
    return build(load_retail_2010_2011())


def test_real_star(real):
    check_integrity(real)
    n, revenue, guest_lines = rows(real, """SELECT count(*), sum(revenue), count(*) FILTER (WHERE customer_key = 0)
                                            FROM fct_sales_line""")[0]
    assert n == 530_105
    assert revenue == pytest.approx(10_666_702.54, abs=0.01)
    assert guest_lines == 132_220
    assert rows(real, "SELECT count(*), count(*) FILTER (WHERE NOT is_merchandise) FROM dim_product") == [(3_922, 22)]
    assert rows(real, "SELECT count(*) FROM dim_customer") == [(4_339,)]
    assert rows(real, "SELECT count(*) FROM dim_date") == [(374,)]
    assert rows(real, "SELECT description FROM dim_product WHERE stock_code = '85123A'") == [("WHITE HANGING HEART T-LIGHT HOLDER",)]
