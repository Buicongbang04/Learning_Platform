import random
import sqlite3

import pytest

from testkit import Exercise

ex = Exercise(__file__)

Q1 = (
    "SELECT shipping_limit_date, price FROM order_items "
    "WHERE seller_id = 's042' AND shipping_limit_date >= '2018-06-01' ORDER BY shipping_limit_date"
)
Q2 = (
    "SELECT order_id, order_purchase_timestamp FROM orders WHERE order_status = 'processing' "
    "AND order_purchase_timestamp >= '2018-03-01' AND order_purchase_timestamp < '2018-04-01'"
)
Q3 = (
    "SELECT o.order_id, SUM(i.price) FROM orders o JOIN order_items i ON i.order_id = o.order_id "
    "WHERE o.customer_id = 'c00042' GROUP BY o.order_id"
)


def build():
    con = sqlite3.connect(":memory:")
    con.executescript(
        """
        CREATE TABLE orders (order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL,
            order_status TEXT NOT NULL, order_purchase_timestamp TEXT NOT NULL);
        CREATE TABLE order_items (order_id TEXT NOT NULL, order_item_id INTEGER NOT NULL,
            product_id TEXT NOT NULL, seller_id TEXT NOT NULL, shipping_limit_date TEXT NOT NULL,
            price REAL NOT NULL, freight_value REAL NOT NULL);
        """
    )
    rnd = random.Random(42)
    statuses = ["delivered"] * 90 + ["shipped"] * 5 + ["canceled"] * 3 + ["processing"] * 2
    orders, items = [], []
    for i in range(20000):
        oid = f"o{i:06d}"
        ts = f"2018-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d} {rnd.randint(0, 23):02d}:00:00"
        orders.append((oid, f"c{rnd.randint(0, 8000):05d}", rnd.choice(statuses), ts))
        for k in range(1, rnd.randint(1, 3) + 1):
            items.append((oid, k, f"p{rnd.randint(0, 3000):04d}", f"s{rnd.randint(0, 300):03d}",
                          ts[:10], round(rnd.uniform(5, 500), 2), round(rnd.uniform(5, 50), 2)))
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)
    con.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?, ?)", items)
    con.commit()
    return con


@pytest.fixture(scope="module")
def db():
    con = build()
    baseline = {name: con.execute(q).fetchall() for name, q in [("q1", Q1), ("q2", Q2), ("q3", Q3)]}
    con.executescript(ex.read("indexes.sql"))
    con.execute("ANALYZE")
    yield con, baseline
    con.close()


def plan(con, sql):
    return [row[3] for row in con.execute("EXPLAIN QUERY PLAN " + sql).fetchall()]


def test_index_budget(db):
    con, _ = db
    names = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL"
    ).fetchall()]
    assert 1 <= len(names) <= 4, f"Cần 1–4 index, đang có {names}"


def test_q1_covering_no_sort(db):
    con, _ = db
    steps = plan(con, Q1)
    text = " | ".join(steps)
    assert "COVERING INDEX" in text, text
    assert "seller_id=? AND shipping_limit_date>" in text, text
    assert "TEMP B-TREE" not in text, text


def test_q2_composite(db):
    con, _ = db
    text = " | ".join(plan(con, Q2))
    assert text.startswith("SEARCH"), text
    assert "order_status=?" in text and "order_purchase_timestamp>" in text and "order_purchase_timestamp<" in text, text


def test_q3_no_scan(db):
    con, _ = db
    steps = plan(con, Q3)
    assert not any(s.startswith("SCAN") for s in steps), steps
    items_step = [s for s in steps if s.startswith("SEARCH i ")]
    assert items_step and "COVERING INDEX" in items_step[0], steps


def test_results_unchanged(db):
    con, baseline = db
    assert sorted(con.execute(Q1).fetchall()) == sorted(baseline["q1"])
    assert sorted(con.execute(Q2).fetchall()) == sorted(baseline["q2"])
    assert sorted(con.execute(Q3).fetchall()) == sorted(baseline["q3"])
