import datetime as dt
import re

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

CATEGORIES = [
    (1, None, "Casa"),
    (2, 1, "Moveis"),
    (3, 2, "Moveis Escritorio"),
    (4, 2, "Moveis Sala"),
    (5, 1, "Cama Mesa Banho"),
    (6, None, "Tecnologia"),
    (7, 6, "Informatica"),
    (8, 7, "Pcs"),
]
PRODUCTS = [("p1", 3), ("p2", 4), ("p3", 5), ("p4", 8), ("p5", 7), ("p6", 2), ("p7", 3)]
ITEMS = [
    ("o1", "p1", 100.00),
    ("o2", "p1", 50.00),
    ("o3", "p2", 200.00),
    ("o4", "p3", 30.00),
    ("o5", "p4", 1000.00),
    ("o6", "p5", 20.00),
    ("o7", "p6", 10.00),
]
DAILY_SALES = [
    ("2018-01-01", 10.00),
    ("2018-01-01", 5.00),
    ("2018-01-03", 7.00),
    ("2018-01-06", 3.00),
]
ORDERS = [
    ("o1", "c1", "2017-11-05 10:00:00"),
    ("o2", "c1", "2017-12-20 10:00:00"),
    ("o3", "c1", "2018-01-02 10:00:00"),
    ("o4", "c1", "2018-01-25 10:00:00"),
    ("o5", "c1", "2018-03-01 10:00:00"),
    ("o6", "c2", "2018-01-10 10:00:00"),
    ("o7", "c2", "2018-03-10 10:00:00"),
    ("o8", "c2", "2018-05-10 10:00:00"),
    ("o9", "c3", "2018-02-01 10:00:00"),
    ("o10", "c3", "2018-03-01 10:00:00"),
    ("o11", "c3", "2018-05-01 10:00:00"),
    ("o12", "c3", "2018-06-01 10:00:00"),
    ("o13", "c3", "2018-07-01 10:00:00"),
    ("o14", "c3", "2018-08-31 23:59:59"),
]


@pytest.fixture(scope="module")
def con():
    con = duckdb.connect()
    con.execute("CREATE TABLE categories (category_id INTEGER, parent_id INTEGER, name VARCHAR)")
    con.execute("CREATE TABLE products (product_id VARCHAR, category_id INTEGER)")
    con.execute("CREATE TABLE order_items (order_id VARCHAR, product_id VARCHAR, price DECIMAL(10, 2))")
    con.execute("CREATE TABLE daily_sales (sale_date DATE, amount DECIMAL(10, 2))")
    con.execute("CREATE TABLE orders (order_id VARCHAR, customer_id VARCHAR, order_purchase_timestamp TIMESTAMP)")
    con.executemany("INSERT INTO categories VALUES (?, ?, ?)", CATEGORIES)
    con.executemany("INSERT INTO products VALUES (?, ?)", PRODUCTS)
    con.executemany("INSERT INTO order_items VALUES (?, ?, ?)", ITEMS)
    con.executemany("INSERT INTO daily_sales VALUES (?, ?)", DAILY_SALES)
    con.executemany("INSERT INTO orders VALUES (?, ?, ?)", ORDERS)
    yield con
    con.close()


def run(con, name):
    rel = con.execute(ex.read(name))
    return [d[0] for d in rel.description], rel.fetchall()


def uses_recursive(name):
    sql = re.sub(r"--[^\n]*", "", ex.read(name)).upper()
    return "WITH RECURSIVE" in " ".join(sql.split())


def test_category_tree(con):
    cols, rows = run(con, "category_tree.sql")
    assert cols == ["category_id", "name", "depth", "path"]
    assert [(r[0], int(r[2]), r[3]) for r in rows] == [
        (1, 0, "Casa"),
        (5, 1, "Casa > Cama Mesa Banho"),
        (2, 1, "Casa > Moveis"),
        (3, 2, "Casa > Moveis > Moveis Escritorio"),
        (4, 2, "Casa > Moveis > Moveis Sala"),
        (6, 0, "Tecnologia"),
        (7, 1, "Tecnologia > Informatica"),
        (8, 2, "Tecnologia > Informatica > Pcs"),
    ]
    assert uses_recursive("category_tree.sql"), "Cần dùng WITH RECURSIVE"


def test_category_tree_handles_deeper_levels(con):
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute("INSERT INTO categories VALUES (9, 8, 'Notebooks'), (10, 9, 'Gamer')")
        _, rows = run(con, "category_tree.sql")
        deepest = [r for r in rows if r[0] == 10][0]
        assert int(deepest[2]) == 4
        assert deepest[3] == "Tecnologia > Informatica > Pcs > Notebooks > Gamer"
    finally:
        con.execute("ROLLBACK")


def test_category_rollup(con):
    cols, rows = run(con, "category_rollup.sql")
    assert cols == ["category_id", "name", "own_revenue", "total_revenue"]
    got = [(r[0], float(r[2]), float(r[3])) for r in rows]
    assert got == [
        (1, 0.0, 390.0),
        (2, 10.0, 360.0),
        (3, 150.0, 150.0),
        (4, 200.0, 200.0),
        (5, 30.0, 30.0),
        (6, 0.0, 1020.0),
        (7, 20.0, 1020.0),
        (8, 1000.0, 1000.0),
    ]
    assert uses_recursive("category_rollup.sql"), "Cần dùng WITH RECURSIVE"


def test_daily_sales_filled(con):
    cols, rows = run(con, "daily_sales_filled.sql")
    assert cols == ["sale_date", "amount"]
    got = [(r[0], float(r[1])) for r in rows]
    assert got == [
        (dt.date(2018, 1, 1), 15.0),
        (dt.date(2018, 1, 2), 0.0),
        (dt.date(2018, 1, 3), 7.0),
        (dt.date(2018, 1, 4), 0.0),
        (dt.date(2018, 1, 5), 0.0),
        (dt.date(2018, 1, 6), 3.0),
    ]


def test_customer_streaks(con):
    cols, rows = run(con, "customer_streaks.sql")
    assert cols == ["customer_id", "longest_streak"]
    assert [(r[0], int(r[1])) for r in rows] == [("c1", 3), ("c2", 1), ("c3", 4)]
