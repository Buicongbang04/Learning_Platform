import datetime as dt

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

CUSTOMERS = [("c3", "rio de janeiro", "RJ"), ("c1", "sao paulo", "SP"), ("c2", "campinas", "SP")]
PRODUCTS = [("p2", "toys"), ("p1", "books"), ("p3", None)]
ORDERS = [
    ("o1", "c1", "delivered", "2024-03-01 10:00:00"),
    ("o2", "c2", "delivered", "2024-03-02 11:00:00"),
    ("o3", "c3", "canceled", "2024-03-02 12:00:00"),
    ("o4", "c1", "delivered", "2024-03-09 09:00:00"),
]
ITEMS = [
    ("o1", 1, "p1", 100.0, 10.0),
    ("o1", 2, "p2", 50.0, 5.0),
    ("o2", 1, "p3", 30.0, 3.0),
    ("o3", 1, "p1", 100.0, 10.0),
    ("o4", 1, "p2", 50.0, 5.0),
    ("o4", 2, "p_ghost", 20.0, 2.0),
]


def build(con):
    con.execute("CREATE TABLE stg_customers (customer_id VARCHAR, customer_city VARCHAR, customer_state VARCHAR)")
    con.executemany("INSERT INTO stg_customers VALUES (?, ?, ?)", CUSTOMERS)
    con.execute("CREATE TABLE stg_products (product_id VARCHAR, product_category_name VARCHAR)")
    con.executemany("INSERT INTO stg_products VALUES (?, ?)", PRODUCTS)
    con.execute(
        "CREATE TABLE stg_orders (order_id VARCHAR, customer_id VARCHAR, order_status VARCHAR,"
        " order_purchase_timestamp TIMESTAMP)"
    )
    con.executemany("INSERT INTO stg_orders VALUES (?, ?, ?, ?)", ORDERS)
    con.execute(
        "CREATE TABLE stg_order_items (order_id VARCHAR, order_item_id INTEGER, product_id VARCHAR,"
        " price DOUBLE, freight_value DOUBLE)"
    )
    con.executemany("INSERT INTO stg_order_items VALUES (?, ?, ?, ?, ?)", ITEMS)


@pytest.fixture
def con():
    con = duckdb.connect()
    build(con)
    con.execute(ex.read("mart.sql"))
    yield con
    con.close()


def one(con, sql):
    return con.execute(sql).fetchone()[0]


def test_dim_customer(con):
    rows = con.execute("SELECT customer_key, customer_id, customer_state FROM dim_customer ORDER BY customer_key").fetchall()
    assert rows == [(0, "unknown", "unknown"), (1, "c1", "SP"), (2, "c2", "SP"), (3, "c3", "RJ")]


def test_dim_product(con):
    rows = con.execute("SELECT product_key, product_id, category FROM dim_product ORDER BY product_key").fetchall()
    assert rows == [(0, "unknown", "unknown"), (1, "p1", "books"), (2, "p2", "toys"), (3, "p3", "unknown")]


def test_dim_date(con):
    rows = con.execute(
        "SELECT date_key, full_date, day_of_week, is_weekend FROM dim_date ORDER BY full_date"
    ).fetchall()
    assert len(rows) == 9  # 2024-03-01 .. 2024-03-09
    assert rows[0] == (20240301, dt.date(2024, 3, 1), 5, False)
    assert rows[1] == (20240302, dt.date(2024, 3, 2), 6, True)
    assert rows[2][3] is True
    assert rows[-1][0] == 20240309
    assert one(con, "SELECT count(DISTINCT date_key) FROM dim_date") == 9


def test_fact_grain_and_counts(con):
    assert one(con, "SELECT count(*) FROM fact_order_items") == len(ITEMS)
    assert one(con, "SELECT count(*) FROM (SELECT DISTINCT order_id, order_item_id FROM fact_order_items)") == len(ITEMS)


def test_fact_no_orphans(con):
    assert one(con, """SELECT count(*) FROM fact_order_items f
                       LEFT JOIN dim_customer d USING (customer_key) WHERE d.customer_key IS NULL""") == 0
    assert one(con, """SELECT count(*) FROM fact_order_items f
                       LEFT JOIN dim_product d USING (product_key) WHERE d.product_key IS NULL""") == 0
    assert one(con, """SELECT count(*) FROM fact_order_items f
                       LEFT JOIN dim_date d USING (date_key) WHERE d.date_key IS NULL""") == 0


def test_fact_reconciles_and_unknown(con):
    assert one(con, "SELECT sum(price) FROM fact_order_items") == pytest.approx(sum(i[3] for i in ITEMS))
    assert one(con, "SELECT sum(total_value) FROM fact_order_items") == pytest.approx(sum(i[3] + i[4] for i in ITEMS))
    assert one(con, "SELECT product_key FROM fact_order_items WHERE order_id = 'o4' AND order_item_id = 2") == 0
    assert one(con, "SELECT customer_key FROM fact_order_items WHERE order_id = 'o1' AND order_item_id = 1") == 1


def test_rerunnable(con):
    con.execute(ex.read("mart.sql"))
    assert one(con, "SELECT count(*) FROM fact_order_items") == len(ITEMS)
    assert one(con, "SELECT count(*) FROM dim_customer") == 4
