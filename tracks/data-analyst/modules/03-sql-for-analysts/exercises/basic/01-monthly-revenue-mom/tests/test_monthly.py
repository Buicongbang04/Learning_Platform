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


def r(invoice, day, qty, price, customer=1, stock="10001"):
    return (invoice, stock, "ITEM", qty, day, price, customer, "United Kingdom")


SMALL = [
    r("1001", "2010-01-05 09:00", 2, 10.0),
    r("1002", "2010-01-20 10:00", 1, 30.0, 2),
    r("C1003", "2010-01-21 10:00", -1, 30.0, 2),     # hoá đơn huỷ
    r("1004", "2010-01-22 10:00", 5, 0.0, 3),        # giá 0
    r("1005", "2010-01-10 18:30", 1, 5.0, None),     # khách vãng lai vẫn là doanh thu
    r("1006", "2010-02-15 10:00", -2, 5.0),          # số lượng âm: tháng 2 không còn dòng hợp lệ
    r("1007", "2010-03-03 11:00", 4, 25.0),
    r("1007", "2010-03-03 11:00", 1, 10.0, stock="10002"),  # cùng hoá đơn: 1 đơn
    r("1009", "2011-01-03 08:00", 1, 15.0, 4),
    r("1008", "2011-01-10 08:00", 3, 20.0, 4),       # ngày cuối có dữ liệu
]

KPI_COLUMNS = ["month", "revenue", "orders", "active_days", "mom_pct", "yoy_pct", "ytd_revenue", "is_complete"]


def approx_or_none(value, abs_tol):
    return None if value is None else pytest.approx(value, abs=abs_tol)


def test_monthly_kpis_small():
    cols, rows = run(tiny(SMALL), "monthly_kpis.sql")
    assert cols == KPI_COLUMNS
    months = [row[0] for row in rows]
    assert months == [dt.date(2010, m, 1) for m in range(1, 13)] + [dt.date(2011, 1, 1)], (
        "Mỗi tháng từ tháng đầu tới tháng cuối một dòng, kể cả tháng không có dòng hợp lệ")
    by_month = {row[0]: row for row in rows}
    jan, feb, mar, apr, may = (by_month[dt.date(2010, m, 1)] for m in range(1, 6))
    jan11 = by_month[dt.date(2011, 1, 1)]
    assert [float(x) for x in (jan[1], feb[1], mar[1], apr[1], jan11[1])] == pytest.approx([55, 0, 110, 0, 75])
    assert (jan[2], jan[3], feb[2], feb[3], mar[2], mar[3]) == (3, 3, 0, 0, 1, 1), "orders = số hoá đơn, active_days = số ngày"
    assert jan[4] is None and jan[5] is None
    assert feb[4] == pytest.approx(-1.0, abs=1e-4)
    assert mar[4] is None, "Tháng trước bằng 0: MoM là NULL, không phải lỗi chia cho 0 hay vô cực"
    assert apr[4] == pytest.approx(-1.0, abs=1e-4) and may[4] is None
    assert jan11[5] == pytest.approx(75 / 55 - 1, abs=1e-4), "YoY so với cùng tháng năm trước"
    assert all(row[5] is None for row in rows[:12])
    assert [float(row[6]) for row in rows] == pytest.approx([55, 55] + [165] * 10 + [75]), "Luỹ kế reset mỗi năm"
    assert [row[7] for row in rows] == [True] * 12 + [False], "Tháng cuối chỉ có dữ liệu tới ngày 10"


def test_monthly_kpis_month_complete_when_data_reaches_month_end():
    rows = [r("1", "2011-01-31 17:00", 1, 10.0), r("2", "2011-02-01 09:00", 1, 10.0)]
    _, out = run(tiny(rows[:1]), "monthly_kpis.sql")
    assert [row[7] for row in out] == [True], "Có dữ liệu tới ngày cuối tháng: tháng đó đủ"
    _, out = run(tiny(rows), "monthly_kpis.sql")
    assert [row[7] for row in out] == [True, False]


PERIODS = ["mtd", "mtd_prev_month", "mtd_prev_year", "ytd", "ytd_prev_year"]


def test_same_period_compare_small():
    cols, rows = run(tiny(SMALL), "same_period_compare.sql")
    assert cols == ["period", "start_date", "end_date", "revenue"]
    assert [row[0] for row in rows] == PERIODS
    d = dt.date
    assert [(row[1], row[2]) for row in rows] == [
        (d(2011, 1, 1), d(2011, 1, 10)), (d(2010, 12, 1), d(2010, 12, 10)), (d(2010, 1, 1), d(2010, 1, 10)),
        (d(2011, 1, 1), d(2011, 1, 10)), (d(2010, 1, 1), d(2010, 1, 10)),
    ]
    # 10/01/2010 18:30 nằm trong kỳ (end_date tính cả ngày); 20/01/2010 thì không
    assert [float(row[3]) for row in rows] == pytest.approx([75, 0, 25, 75, 25])


def test_same_period_compare_clamps_short_month():
    rows = [
        r("1", "2010-02-10 10:00", 1, 9.0), r("2", "2010-03-30 23:00", 1, 3.0), r("3", "2010-03-31 09:00", 1, 100.0),
        r("4", "2011-01-15 10:00", 1, 50.0), r("5", "2011-02-28 10:00", 1, 40.0), r("6", "2011-03-01 10:00", 1, 7.0),
        r("7", "2011-03-30 16:00", 1, 10.0),
    ]
    _, out = run(tiny(rows), "same_period_compare.sql")
    d = dt.date
    assert [(row[0], row[1], row[2]) for row in out] == [
        ("mtd", d(2011, 3, 1), d(2011, 3, 30)),
        ("mtd_prev_month", d(2011, 2, 1), d(2011, 2, 28)),  # tháng 2 không có ngày 30
        ("mtd_prev_year", d(2010, 3, 1), d(2010, 3, 30)),
        ("ytd", d(2011, 1, 1), d(2011, 3, 30)),
        ("ytd_prev_year", d(2010, 1, 1), d(2010, 3, 30)),
    ]
    assert [float(row[3]) for row in out] == pytest.approx([17, 40, 3, 107, 12])


def test_real_monthly_kpis(real):
    cols, rows = run(real, "monthly_kpis.sql")
    assert cols == KPI_COLUMNS
    by_month = {row[0]: row for row in rows}
    assert len(rows) == 25 and rows[0][0] == dt.date(2009, 12, 1) and rows[-1][0] == dt.date(2011, 12, 1)
    nov, dec = by_month[dt.date(2011, 11, 1)], by_month[dt.date(2011, 12, 1)]
    assert float(nov[1]) == pytest.approx(1_509_496.33, abs=0.01)
    assert nov[2] == 2769 and nov[3] == 26
    assert nov[4] == pytest.approx(0.3069, abs=1e-4) and nov[5] == pytest.approx(0.0267, abs=1e-4)
    assert float(nov[6]) == pytest.approx(9_204_145.72, abs=0.01)
    assert dec[3] == 8 and dec[4] == pytest.approx(-0.5768, abs=1e-4) and dec[7] is False
    assert sum(float(row[1]) for row in rows) == pytest.approx(20_533_741.92, abs=0.05)
    assert by_month[dt.date(2010, 12, 1)][5] == pytest.approx(-0.0023, abs=1e-4)


def test_real_same_period_compare(real):
    _, rows = run(real, "same_period_compare.sql")
    got = {row[0]: (row[1], row[2], float(row[3])) for row in rows}
    assert got["mtd"] == (dt.date(2011, 12, 1), dt.date(2011, 12, 9), pytest.approx(638_810.68, abs=0.01))
    assert got["mtd_prev_month"][2] == pytest.approx(454_238.30, abs=0.01)
    assert got["mtd_prev_year"][2] == pytest.approx(438_852.65, abs=0.01)
    assert got["ytd"][2] == pytest.approx(9_842_956.40, abs=0.01)
    assert got["ytd_prev_year"] == (dt.date(2010, 1, 1), dt.date(2010, 12, 9), pytest.approx(9_480_206.26, abs=0.01))
