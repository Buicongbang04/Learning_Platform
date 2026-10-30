import datetime as dt
import os
import tempfile
import uuid
from pathlib import Path

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Bản chuẩn của loader Online Retail II: exercises/basic/01-monthly-revenue-mom/tests/test_monthly.py.
# Các bài khác của module chép y hệt; sửa thì sửa mọi bản.
SHEETS = ("Year 2009-2010", "Year 2010-2011")  # sheet đầu chứa lại 01-09/12/2010 của sheet sau: bỏ phần trùng
CACHE_DIR = Path(tempfile.gettempdir()) / "da-cache"  # cache parquet, không ghi vào data/raw (thư mục dùng chung)


def _sql_path(path: Path) -> str:
    return str(path).replace("'", "''")


def _sheet_sql(xlsx: Path, sheet: str) -> str:
    return f"""
        SELECT Invoice AS invoice, StockCode AS stock_code, Description AS description,
               CAST(CAST(Quantity AS DOUBLE) AS INTEGER) AS quantity,
               TIMESTAMP '1899-12-30' + to_seconds(CAST(round(CAST(InvoiceDate AS DOUBLE) * 86400) AS BIGINT))
                   AS invoice_date,
               CAST(Price AS DOUBLE) AS price,
               CAST(CAST("Customer ID" AS DOUBLE) AS INTEGER) AS customer_id,
               Country AS country
        FROM read_xlsx('{_sql_path(xlsx)}', sheet = '{sheet}', all_varchar = true)"""


def _excel_extension_missing(exc: duckdb.Error) -> bool:
    """Chỉ lỗi cài/nạp extension excel (máy offline...). Lỗi SQL hay lỗi dữ liệu thì phải nổi lên."""
    kinds = (duckdb.CatalogException, duckdb.IOException, duckdb.HTTPException)
    return isinstance(exc, kinds) and "extension" in str(exc).lower()


def _load_with_pandas(con: duckdb.DuckDBPyConnection, xlsx: Path) -> None:
    import pandas as pd

    old, new = (pd.read_excel(xlsx, sheet_name=s) for s in SHEETS)
    df = pd.concat([old[old.InvoiceDate < "2010-12-01"], new], ignore_index=True)
    df = pd.DataFrame({
        "invoice": df["Invoice"].astype(str), "stock_code": df["StockCode"].astype(str),
        "description": df["Description"], "quantity": df["Quantity"].astype("int32"),
        "invoice_date": df["InvoiceDate"], "price": df["Price"].astype(float),
        "customer_id": df["Customer ID"].astype("Int32"), "country": df["Country"],
    })
    con.register("online_retail_df", df)
    con.execute("CREATE TABLE online_retail AS SELECT * FROM online_retail_df")
    con.unregister("online_retail_df")


def load_online_retail(con: duckdb.DuckDBPyConnection, xlsx: Path) -> None:
    """Bảng `online_retail`: hai sheet gộp, đúng dữ liệu gốc (chưa lọc hoá đơn huỷ, giá 0...).

    Lần đầu đọc xlsx (extension excel của DuckDB ~8 giây; máy không cài được extension thì pandas ~60-90 giây)
    rồi ghi cache parquet vào thư mục tạm của hệ điều hành, khoá theo mtime và kích thước tệp xlsx; các lần sau
    đọc cache trong khoảng 1 giây.
    """
    stat = xlsx.stat()
    cache = CACHE_DIR / f"online_retail_ii_{stat.st_mtime_ns}_{stat.st_size}.parquet"
    if cache.exists():
        try:
            con.execute(f"CREATE TABLE online_retail AS SELECT * FROM read_parquet('{_sql_path(cache)}')")
            return
        except duckdb.IOException:  # cache hỏng: đọc lại từ xlsx và ghi đè
            pass
    try:
        con.execute(
            f"CREATE TABLE online_retail AS SELECT * FROM ({_sheet_sql(xlsx, SHEETS[0])}) "
            f"WHERE invoice_date < TIMESTAMP '2010-12-01' UNION ALL {_sheet_sql(xlsx, SHEETS[1])}"
        )
    except duckdb.Error as exc:
        if not _excel_extension_missing(exc):
            raise
        _load_with_pandas(con, xlsx)
    tmp = CACHE_DIR / f".{cache.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:  # ghi atomic: tệp tạm tên riêng rồi rename, an toàn khi nhiều test chạy song song
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        con.execute(f"COPY online_retail TO '{_sql_path(tmp)}' (FORMAT parquet)")
        os.replace(tmp, cache)
    except (OSError, duckdb.Error):  # không ghi được cache thì thôi, lần sau đọc lại xlsx
        tmp.unlink(missing_ok=True)


COLUMNS = ("invoice VARCHAR, stock_code VARCHAR, description VARCHAR, quantity INTEGER, invoice_date TIMESTAMP, "
           "price DOUBLE, customer_id INTEGER, country VARCHAR")


def tiny(rows) -> duckdb.DuckDBPyConnection:
    """Bảng online_retail nhỏ, cùng schema với bảng thật."""
    con = duckdb.connect()
    con.execute(f"CREATE TABLE online_retail ({COLUMNS})")
    con.executemany("INSERT INTO online_retail VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    return con


def run(con, name):
    rel = con.execute(ex.read(name))
    return [d[0] for d in rel.description], rel.fetchall()


@pytest.fixture(scope="module")
def real():
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    load_online_retail(con, xlsx)
    yield con
    con.close()


def r(customer, day, qty=1, price=10.0, invoice="1001"):
    return (invoice, "10001", "ITEM", qty, day, price, customer, "United Kingdom")


SMALL = [
    r(1, "2010-01-04 10:00"), r(1, "2010-02-08 10:00"), r(1, "2010-04-12 10:00"),
    r(1, "2010-05-10 09:00"),                                  # tháng 5 chưa đủ: không tính
    r(2, "2010-01-05 10:00"), r(2, "2010-02-09 10:00", -1, invoice="C2001"),   # chỉ có hoá đơn huỷ ở tháng 2
    r(6, "2010-01-20 10:00"), r(6, "2010-01-25 10:00"),        # hai lần trong cùng tháng đầu
    r(3, "2010-01-15 10:00", price=0.0),                       # giá 0 không phải lần mua đầu
    r(3, "2010-02-03 10:00"), r(3, "2010-03-03 10:00"),
    r(7, "2010-03-10 10:00"),
    r(4, "2010-04-30 16:00"),
    r(5, "2010-05-04 10:00"),                                  # cohort tháng 5 chưa đủ: không có dòng
    r(None, "2010-01-06 10:00"),                               # khách vãng lai không thuộc cohort nào
]

LONG_COLUMNS = ["cohort_month", "month_number", "cohort_size", "active_customers", "retention"]
EXPECTED_LONG = [
    ("2010-01-01", 0, 3, 3, 1.0), ("2010-01-01", 1, 3, 1, 1 / 3), ("2010-01-01", 2, 3, 0, 0.0),
    ("2010-01-01", 3, 3, 1, 1 / 3),
    ("2010-02-01", 0, 1, 1, 1.0), ("2010-02-01", 1, 1, 1, 1.0), ("2010-02-01", 2, 1, 0, 0.0),
    ("2010-03-01", 0, 1, 1, 1.0), ("2010-03-01", 1, 1, 0, 0.0),
    ("2010-04-01", 0, 1, 1, 1.0),
]


def normalize_long(rows):
    return [(str(c), int(k), int(n), int(a), pytest.approx(float(x), abs=1e-4)) for c, k, n, a, x in rows]


def test_cohort_retention_small():
    cols, rows = run(tiny(SMALL), "cohort_retention.sql")
    assert cols == LONG_COLUMNS
    assert normalize_long(rows) == EXPECTED_LONG, (
        "Mỗi cohort một dòng cho mọi tháng k quan sát được (kể cả k không ai quay lại), bỏ tháng chưa đủ")


def test_cohort_retention_last_month_complete_when_data_reaches_month_end():
    rows = [row for row in SMALL if not str(row[4]).startswith("2010-05")]   # dữ liệu dừng 30/04 16:00
    _, out = run(tiny(rows), "cohort_retention.sql")
    assert normalize_long(out) == EXPECTED_LONG


SUMMARY_COLUMNS = ["cohort_month", "cohort_size", "m1", "m3", "m6", "m12"]


def maybe(value):
    return None if value is None else pytest.approx(float(value), abs=1e-4)


def test_retention_summary_small():
    cols, rows = run(tiny(SMALL), "retention_summary.sql")
    assert cols == SUMMARY_COLUMNS
    got = [(str(c), int(n), *(maybe(v) for v in vals)) for c, n, *vals in rows]
    assert got == [
        ("2010-01-01", 3, 1 / 3, 1 / 3, None, None),
        ("2010-02-01", 1, 1.0, None, None, None),
        ("2010-03-01", 1, 0.0, None, None, None),   # quan sát được và không ai quay lại: 0, không phải NULL
        ("2010-04-01", 1, None, None, None, None),  # chưa quan sát được tháng 1: NULL, không phải 0
    ]


def test_real_cohort_retention(real):
    cols, rows = run(real, "cohort_retention.sql")
    assert cols == LONG_COLUMNS
    assert len(rows) == 300
    sizes = {str(row[0]): int(row[2]) for row in rows}
    assert len(sizes) == 24 and sum(sizes.values()) == 5850
    assert sizes["2009-12-01"] == 955 and sizes["2010-12-01"] == 76 and sizes["2011-11-01"] == 191
    cell = {(str(row[0]), int(row[1])): float(row[4]) for row in rows}
    assert cell[("2009-12-01", 1)] == pytest.approx(0.3529, abs=1e-4)
    assert cell[("2009-12-01", 11)] == pytest.approx(0.4953, abs=1e-4)
    assert ("2009-12-01", 24) not in cell, "Tháng 12/2011 chưa đủ, không tính"


def test_real_retention_summary(real):
    _, rows = run(real, "retention_summary.sql")
    assert len(rows) == 24
    by = {str(row[0]): row for row in rows}
    assert float(by["2011-10-01"][2]) == pytest.approx(0.3213, abs=1e-4) and by["2011-10-01"][3] is None
    assert by["2011-11-01"][2] is None
    assert float(by["2010-11-01"][5]) == pytest.approx(0.2554, abs=1e-4)
    assert by["2010-12-01"][5] is None
