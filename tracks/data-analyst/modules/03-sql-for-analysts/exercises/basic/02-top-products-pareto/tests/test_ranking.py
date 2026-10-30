import datetime as dt
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


def r(country, stock, qty, price, day="2011-01-05 10:00", invoice="1001"):
    return (invoice, stock, "ITEM", qty, day, price, 1, country)


SMALL = [
    r("France", "20001", 10, 3.0),
    r("France", "20002", 5, 4.0),
    r("France", "20003", 2, 10.0),                         # hoà với 20002: mã nhỏ hơn đứng trước
    r("France", "20004", 1, 5.0),
    r("France", "POST", 1, 100.0),                         # phí vận chuyển, không phải hàng hoá
    r("France", "20005", 1, 1000.0, "2011-12-02 10:00"),   # ngoài kỳ
    r("France", "20004", 50, 2.0, invoice="C2001"),        # hoá đơn huỷ
    r("France", "20004", 3, 0.0),                          # giá 0
    r("Germany", "85123A", 2, 25.0),                       # mã có chữ cái phía sau vẫn là hàng hoá
    r("Germany", "30001", 3, 10.0, "2010-12-01 00:00"),    # mốc đầu kỳ: tính
    r("Germany", "30001", 1, 10.0, "2011-11-30 23:59"),
    r("Germany", "DOT", 1, 500.0),
    r("Germany", "30002", 9, 10.0, "2010-11-30 23:00"),    # trước kỳ
    r("Japan", "POST", 2, 40.0),                           # Japan không có hàng hoá trong kỳ
]


def test_top3_small():
    cols, rows = run(tiny(SMALL), "top3_per_country.sql")
    assert cols == ["country", "rnk", "stock_code", "revenue", "share_of_country"]
    got = [(c, int(k), s, float(v), float(sh)) for c, k, s, v, sh in rows]
    assert got == [
        ("France", 1, "20001", pytest.approx(30.0), pytest.approx(0.4, abs=1e-4)),
        ("France", 2, "20002", pytest.approx(20.0), pytest.approx(20 / 75, abs=1e-4)),
        ("France", 3, "20003", pytest.approx(20.0), pytest.approx(20 / 75, abs=1e-4)),
        ("Germany", 1, "85123A", pytest.approx(50.0), pytest.approx(50 / 90, abs=1e-4)),
        ("Germany", 2, "30001", pytest.approx(40.0), pytest.approx(40 / 90, abs=1e-4)),
    ], "Top 3 hàng hoá mỗi nước, đúng kỳ, bỏ phí; hoà thì mã nhỏ hơn trước; tỉ trọng trên doanh thu hàng hoá của nước"


def test_pareto_small():
    cols, rows = run(tiny(SMALL), "pareto.sql")
    assert cols == ["stock_code", "revenue", "rnk", "cum_share", "abc_class"]
    assert [row[0] for row in rows] == ["85123A", "30001", "20001", "20002", "20003", "20004"]
    assert [int(row[2]) for row in rows] == [1, 2, 3, 4, 5, 6]
    assert [float(row[1]) for row in rows] == pytest.approx([50, 40, 30, 20, 20, 5])
    assert [float(row[3]) for row in rows] == pytest.approx([50 / 165, 90 / 165, 120 / 165, 140 / 165, 160 / 165, 1.0], abs=1e-4)
    # nhóm theo luỹ kế TRƯỚC sản phẩm: 0, .30, .55, .73 < 0.8 -> A; .85 < 0.95 -> B; .97 -> C
    assert [row[4] for row in rows] == ["A", "A", "A", "A", "B", "C"]


def test_pareto_class_boundaries():
    rows = [r("UK", f"4000{i}", 1, v) for i, v in enumerate([50.0, 29.0, 11.0, 6.0, 4.0])]
    _, out = run(tiny(rows), "pareto.sql")
    # luỹ kế trước: 0, .50, .79, .90, .96 -> A, A, A, B, C (sản phẩm vượt mốc 80% vẫn là A)
    assert [row[4] for row in out] == ["A", "A", "A", "B", "C"]


def test_real_top3(real):
    _, rows = run(real, "top3_per_country.sql")
    assert len(rows) == 114 and len({row[0] for row in rows}) == 38
    assert all(row[2][:5].isdigit() for row in rows), "Còn mã phí (POST, DOT, M...) trong top 3"
    top = {(row[0], int(row[1])): row for row in rows}
    uk = top[("United Kingdom", 1)]
    assert uk[2] == "22423" and float(uk[3]) == pytest.approx(137_735.07, abs=0.01)
    assert float(uk[4]) == pytest.approx(0.0168, abs=1e-4)
    assert top[("Germany", 1)][2] == "22423" and top[("France", 1)][2] == "23084"
    assert top[("Netherlands", 1)][2] == "22326"


def test_real_pareto(real):
    _, rows = run(real, "pareto.sql")
    assert len(rows) == 3897
    assert rows[0][0] == "22423" and float(rows[0][1]) == pytest.approx(168_477.87, abs=0.01)
    classes = [row[4] for row in rows]
    assert (classes.count("A"), classes.count("B"), classes.count("C")) == (834, 977, 2086)
    assert float(rows[833][3]) == pytest.approx(0.8003, abs=1e-4)
    assert sum(float(row[1]) for row in rows) == pytest.approx(9_655_544.63, abs=0.05)
