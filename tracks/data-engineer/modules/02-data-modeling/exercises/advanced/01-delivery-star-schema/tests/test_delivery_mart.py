"""Hợp đồng tối thiểu của mart giao hàng. Thiết kế đầy đủ được chấm theo rubric."""

import datetime as dt

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

ORDERS = [
    # id, customer, status, purchase, approved, carrier, delivered, estimated
    ("o1", "c1", "delivered", "2018-01-02 10:00", "2018-01-02 12:00", "2018-01-04 09:00", "2018-01-10 15:00", "2018-01-20 00:00"),
    ("o2", "c2", "delivered", "2018-01-05 23:00", "2018-01-06 01:00", "2018-01-08 09:00", "2018-01-25 08:00", "2018-01-22 00:00"),
    ("o3", "c1", "delivered", "2018-02-01 08:00", "2018-02-01 09:00", "2018-02-02 09:00", "2018-02-15 18:00", "2018-02-15 00:00"),
    ("o4", "c3", "shipped", "2018-02-03 08:00", "2018-02-03 09:00", "2018-02-05 09:00", None, "2018-02-25 00:00"),
    ("o5", "c3", "canceled", "2018-02-04 08:00", None, None, None, "2018-02-26 00:00"),
    ("o6", "c4", "delivered", "2018-03-01 08:00", "2018-03-01 09:00", "2018-03-03 09:00", "2018-03-05 10:00", "2018-03-21 00:00"),
]
ITEMS = [
    ("o1", 1, "p1", "s1", 50.0, 10.0), ("o1", 2, "p2", "s2", 30.0, 5.0),
    ("o2", 1, "p1", "s1", 80.0, 20.0),
    ("o3", 1, "p3", "s1", 15.0, 7.5), ("o3", 2, "p3", "s1", 15.0, 7.5), ("o3", 3, "p4", "s3", 99.0, 12.0),
    ("o4", 1, "p2", "s2", 40.0, 9.0), ("o5", 1, "p2", "s2", 40.0, 9.0),
    ("o6", 1, "p5", "s3", 200.0, 25.0),
]
CUSTOMERS = [("c1", "sao paulo", "SP"), ("c2", "rio de janeiro", "RJ"), ("c3", "salvador", "BA"), ("c4", "curitiba", "PR")]
SELLERS = [("s1", "campinas", "SP"), ("s2", "curitiba", "PR"), ("s3", "belo horizonte", "MG")]
REVIEWS = [("r1", "o1", 5), ("r2", "o2", 1), ("r3", "o3", 4), ("r4", "o3", 2), ("r5", "o4", 3)]

EXPECTED = {
    # order_id: (state, purchase_key, delivered_key, estimated_key, delivery_days, is_late, items, freight, review)
    "o1": ("SP", 20180102, 20180110, 20180120, 8, False, 2, 15.0, 5.0),
    "o2": ("RJ", 20180105, 20180125, 20180122, 20, True, 1, 20.0, 1.0),
    "o3": ("SP", 20180201, 20180215, 20180215, 14, False, 3, 27.0, 3.0),
    "o6": ("PR", 20180301, 20180305, 20180321, 4, False, 1, 25.0, None),
}


@pytest.fixture(scope="module")
def con():
    if ex.target.name != "starter" and not (ex.target / "build.sql").exists():
        pytest.skip("Bài advanced không có lời giải dạng code, xem SOLUTION.md")
    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE raw_orders (order_id VARCHAR, customer_id VARCHAR, order_status VARCHAR,
            order_purchase_timestamp TIMESTAMP, order_approved_at TIMESTAMP,
            order_delivered_carrier_date TIMESTAMP, order_delivered_customer_date TIMESTAMP,
            order_estimated_delivery_date TIMESTAMP);
        CREATE TABLE raw_order_items (order_id VARCHAR, order_item_id INTEGER, product_id VARCHAR,
            seller_id VARCHAR, price DOUBLE, freight_value DOUBLE);
        CREATE TABLE raw_customers (customer_id VARCHAR, customer_city VARCHAR, customer_state VARCHAR);
        CREATE TABLE raw_sellers (seller_id VARCHAR, seller_city VARCHAR, seller_state VARCHAR);
        CREATE TABLE raw_reviews (review_id VARCHAR, order_id VARCHAR, review_score INTEGER);
        """
    )
    con.executemany("INSERT INTO raw_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ORDERS)
    con.executemany("INSERT INTO raw_order_items VALUES (?, ?, ?, ?, ?, ?)", ITEMS)
    con.executemany("INSERT INTO raw_customers VALUES (?, ?, ?)", CUSTOMERS)
    con.executemany("INSERT INTO raw_sellers VALUES (?, ?, ?)", SELLERS)
    con.executemany("INSERT INTO raw_reviews VALUES (?, ?, ?)", REVIEWS)
    con.execute(ex.read("build.sql"))
    yield con
    con.close()


def test_grain_one_row_per_delivered_order(con):
    rows = con.execute("SELECT order_id FROM fact_order_delivery ORDER BY order_id").fetchall()
    assert [r[0] for r in rows] == ["o1", "o2", "o3", "o6"]


def test_measures(con):
    rows = con.execute(
        """
        SELECT f.order_id, c.state, f.purchase_date_key, f.delivered_date_key, f.estimated_date_key,
               f.delivery_days, f.is_late, f.items_count, f.total_freight, f.review_score
        FROM fact_order_delivery f JOIN dim_customer c ON c.customer_key = f.customer_key
        """
    ).fetchall()
    got = {
        r[0]: (r[1], int(r[2]), int(r[3]), int(r[4]), int(r[5]), bool(r[6]), int(r[7]),
               float(r[8]), None if r[9] is None else float(r[9]))
        for r in rows
    }
    assert got == EXPECTED


def test_date_keys_resolve(con):
    for col in ("purchase_date_key", "delivered_date_key", "estimated_date_key"):
        orphans = con.execute(
            f"SELECT COUNT(*) FROM fact_order_delivery f LEFT JOIN dim_date d ON d.date_key = f.{col} "
            "WHERE d.date_key IS NULL"
        ).fetchone()[0]
        assert orphans == 0, f"{col} có key không tồn tại trong dim_date"
    assert con.execute("SELECT full_date FROM dim_date WHERE date_key = 20180125").fetchone()[0] == dt.date(2018, 1, 25)


def test_dim_customer_key_unique(con):
    dup = con.execute("SELECT customer_key FROM dim_customer GROUP BY 1 HAVING COUNT(*) > 1").fetchall()
    assert dup == []
