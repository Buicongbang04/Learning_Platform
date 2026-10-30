import datetime as dt
import re
from pathlib import Path

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

SHEETS = ("Year 2009-2010", "Year 2010-2011")  # sheet đầu chứa lại 01-09/12/2010 của sheet sau: bỏ phần trùng


def _sheet_sql(xlsx: Path, sheet: str) -> str:
    path = str(xlsx).replace("'", "''")
    return f"""
        SELECT Invoice AS invoice, StockCode AS stock_code, Description AS description,
               CAST(CAST(Quantity AS DOUBLE) AS INTEGER) AS quantity,
               TIMESTAMP '1899-12-30' + to_seconds(CAST(round(CAST(InvoiceDate AS DOUBLE) * 86400) AS BIGINT))
                   AS invoice_date,
               CAST(Price AS DOUBLE) AS price,
               CAST(CAST("Customer ID" AS DOUBLE) AS INTEGER) AS customer_id,
               Country AS country
        FROM read_xlsx('{path}', sheet = '{sheet}', all_varchar = true)"""


def load_online_retail(con: duckdb.DuckDBPyConnection, xlsx: Path) -> None:
    """Bảng `online_retail`: hai sheet gộp, đúng dữ liệu gốc (chưa lọc hoá đơn huỷ, giá 0...)."""
    try:  # extension excel của DuckDB: ~8 giây
        con.execute(
            f"CREATE TABLE online_retail AS SELECT * FROM ({_sheet_sql(xlsx, SHEETS[0])}) "
            f"WHERE invoice_date < TIMESTAMP '2010-12-01' UNION ALL {_sheet_sql(xlsx, SHEETS[1])}"
        )
    except duckdb.Error:  # không cài được extension (máy offline): đọc bằng pandas, ~50 giây
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


_seq = iter(range(1000, 2000))


def r(customer, country, day, price, qty=1, invoice=None):
    return (invoice or str(next(_seq)), "10001", "ITEM", qty, day, price, customer, country)


SMALL = [
    r(1, "United Kingdom", "2010-01-10 10:00", 100.0),
    r(1, "United Kingdom", "2011-01-10 10:00", 50.0, qty=2),          # khách cũ quay lại
    r(2, "France", "2011-01-15 10:00", 40.0),                        # khách mới
    r(2, "France", "2011-01-20 10:00", 10.0),                        # vẫn là "mới" trong tháng đầu
    r(2, "France", "2011-03-02 10:00", 30.0),                        # tháng sau: returning
    r(None, "France", "2011-03-05 10:00", 5.0, qty=2),               # khách vãng lai
    r(3, "Germany", "2010-06-01 10:00", 80.0),
    r(3, "Germany", "2011-02-01 10:00", 80.0, qty=-1, invoice="C9001"),  # huỷ: không tính
    r(3, "Germany", "2011-03-10 10:00", 20.0),
    r(4, "Germany", "2011-03-11 10:00", 60.0),
    r(4, "Germany", "2011-03-12 10:00", 0.0),                        # giá 0: không tính
    r(5, "Japan", "2011-12-02 10:00", 500.0),                        # sau kỳ 12 tháng
    r(6, "Norway", "2010-02-01 10:00", 50.0),                        # chỉ có ở kỳ trước
]


def test_q1_small():
    cols, rows = run(tiny(SMALL), "q1_revenue_12m.sql")
    assert cols == ["period", "revenue", "orders", "customers", "aov"]
    got = [(p, float(v), int(o), int(c), float(a)) for p, v, o, c, a in rows]
    assert got == [
        ("prev_12m", pytest.approx(230.0), 3, 3, pytest.approx(230 / 3, abs=0.01)),
        ("last_12m", pytest.approx(270.0), 7, 4, pytest.approx(270 / 7, abs=0.01)),
    ]


def test_q2_small():
    cols, rows = run(tiny(SMALL), "q2_new_vs_returning.sql")
    assert cols == ["month", "customer_type", "customers", "revenue"]
    got = [(m, t, int(c), float(v)) for m, t, c, v in rows]
    d = dt.date
    assert got == [
        (d(2011, 1, 1), "new", 1, pytest.approx(50.0)),
        (d(2011, 1, 1), "returning", 1, pytest.approx(100.0)),
        (d(2011, 3, 1), "guest", 0, pytest.approx(10.0)),
        (d(2011, 3, 1), "new", 1, pytest.approx(60.0)),
        (d(2011, 3, 1), "returning", 2, pytest.approx(50.0)),
    ]


def test_q3_small():
    cols, rows = run(tiny(SMALL), "q3_markets.sql")
    assert cols == ["country", "revenue_prev", "revenue_last", "growth_pct", "customers_last", "top_customer_share"]
    assert [row[0] for row in rows] == ["France", "Germany"], "Bỏ UK, chỉ nước có doanh thu kỳ gần nhất"
    france, germany = rows
    assert float(france[1]) == pytest.approx(0.0) and france[3] is None, "Không có kỳ trước: growth NULL"
    assert float(france[2]) == pytest.approx(90.0) and int(france[4]) == 1
    assert float(france[5]) == pytest.approx(80 / 90, abs=1e-4), "Tỉ trọng của khách lớn nhất trên doanh thu cả nước"
    assert float(germany[3]) == pytest.approx(0.0, abs=1e-4) and int(germany[4]) == 2
    assert float(germany[5]) == pytest.approx(0.75, abs=1e-4)


def test_real_answers(real):
    _, q1 = run(real, "q1_revenue_12m.sql")
    assert float(q1[0][1]) == pytest.approx(9_867_039.37, abs=0.01)
    assert float(q1[1][1]) == pytest.approx(10_027_891.86, abs=0.01)
    assert (int(q1[1][2]), int(q1[1][3])) == (19_141, 4_297)
    _, q2 = run(real, "q2_new_vs_returning.sql")
    by_type = {}
    for _, kind, _, revenue in q2:
        by_type[kind] = by_type.get(kind, 0.0) + float(revenue)
    assert by_type["new"] == pytest.approx(754_193.58, abs=0.05)
    assert by_type["returning"] == pytest.approx(7_639_021.53, abs=0.05)
    _, q3 = run(real, "q3_markets.sql")
    assert len(q3) == 10 and q3[0][0] == "EIRE"
    top = {row[0]: row for row in q3}
    assert float(top["Netherlands"][5]) == pytest.approx(0.9809, abs=1e-4)
    assert float(top["France"][3]) == pytest.approx(0.4365, abs=1e-4)


MEMO_HEADINGS = ["## Trả lời ngắn", "## Câu 1", "## Câu 2", "## Câu 3", "## Định nghĩa và giới hạn", "## Đề xuất"]


def test_memo_written():
    memo = ex.read("MEMO.md")
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 200 <= words <= 600, f"Memo ngắn: 200-600 từ, hiện có {words}"
    title = memo.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in MEMO_HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"
    for part in re.split(r"\n## ", memo)[1:]:
        if part.startswith("Câu"):
            assert re.search(r"\d", part.split("\n", 1)[1]), f"Mục '{part.splitlines()[0]}' cần ít nhất một con số"
