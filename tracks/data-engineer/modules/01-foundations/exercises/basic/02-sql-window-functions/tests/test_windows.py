import datetime as dt
import re

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

SELLERS = [("s1", "SP"), ("s2", "SP"), ("s3", "SP"), ("s6", "SP"), ("s4", "PR"), ("s5", "PR")]
ORDERS = [
    ("o1", "c1", "delivered", "2018-01-30 10:00:00"),
    ("o2", "c2", "delivered", "2018-01-31 09:00:00"),
    ("o3", "c1", "delivered", "2018-02-01 23:00:00"),
    ("o4", "c3", "canceled", "2018-02-01 08:00:00"),
    ("o5", "c2", "delivered", "2018-02-03 12:00:00"),
    ("o6", "c1", "delivered", "2018-02-03 13:00:00"),
]
ITEMS = [
    ("o1", 1, "s1", 100.00),
    ("o1", 2, "s4", 20.00),
    ("o2", 1, "s2", 60.00),
    ("o3", 1, "s2", 40.00),
    ("o3", 2, "s5", 30.00),
    ("o4", 1, "s3", 500.00),
    ("o5", 1, "s3", 70.00),
    ("o5", 2, "s4", 10.00),
    ("o6", 1, "s5", 50.00),
    ("o6", 2, "s6", 10.00),
]


@pytest.fixture(scope="module")
def con():
    con = duckdb.connect()
    con.execute("CREATE TABLE sellers (seller_id VARCHAR, seller_state VARCHAR)")
    con.execute(
        "CREATE TABLE orders (order_id VARCHAR, customer_id VARCHAR, order_status VARCHAR, "
        "order_purchase_timestamp TIMESTAMP)"
    )
    con.execute(
        "CREATE TABLE order_items (order_id VARCHAR, order_item_id INTEGER, seller_id VARCHAR, "
        "price DECIMAL(10, 2))"
    )
    con.executemany("INSERT INTO sellers VALUES (?, ?)", SELLERS)
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", ORDERS)
    con.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?)", ITEMS)
    yield con
    con.close()


def run(con, name):
    sql = ex.read(name)
    rel = con.execute(sql)
    cols = [d[0] for d in rel.description]
    return cols, rel.fetchall()


def test_top_sellers(con):
    cols, rows = run(con, "top_sellers.sql")
    assert cols == ["seller_state", "seller_id", "revenue", "rnk"]
    got = [(s, sid, float(rev), int(rnk)) for s, sid, rev, rnk in rows]
    assert got == [
        ("PR", "s5", 80.0, 1),
        ("PR", "s4", 30.0, 2),
        ("SP", "s1", 100.0, 1),
        ("SP", "s2", 100.0, 1),
        ("SP", "s3", 70.0, 2),
    ]


def test_daily_revenue(con):
    cols, rows = run(con, "daily_revenue.sql")
    assert cols == ["order_date", "revenue", "mtd_revenue", "ma3"]
    got = [(d, float(r), float(m), float(a)) for d, r, m, a in rows]
    expected = [
        (dt.date(2018, 1, 30), 120.0, 120.0, 120.0),
        (dt.date(2018, 1, 31), 60.0, 180.0, 90.0),
        (dt.date(2018, 2, 1), 70.0, 70.0, 83.33),
        (dt.date(2018, 2, 3), 140.0, 210.0, 90.0),
    ]
    assert len(got) == len(expected)
    for g, e in zip(got, expected):
        assert g[0] == e[0]
        assert g[1:] == pytest.approx(e[1:], abs=0.006)


def test_customer_order_gaps(con):
    cols, rows = run(con, "customer_order_gaps.sql")
    assert cols == ["customer_id", "order_id", "order_purchase_timestamp", "order_seq", "days_since_prev"]
    got = [(c, o, int(seq), None if gap is None else int(gap)) for c, o, _, seq, gap in rows]
    assert got == [
        ("c1", "o1", 1, None),
        ("c1", "o3", 2, 2),
        ("c1", "o6", 3, 2),
        ("c2", "o2", 1, None),
        ("c2", "o5", 2, 3),
        ("c3", "o4", 1, None),
    ]


@pytest.mark.parametrize("name", ["top_sellers.sql", "daily_revenue.sql", "customer_order_gaps.sql"])
def test_uses_window_functions(name):
    sql = re.sub(r"--[^\n]*", "", ex.read(name)).upper()   # bỏ comment
    assert re.search(r"\bOVER\s*(\(|\w)", sql), f"{name} cần dùng window function (OVER ...)"
