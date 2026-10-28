"""Hợp đồng tối thiểu cho pipeline nạp Olist. Chấm đầy đủ theo rubric trong SOLUTION.md."""

import sqlite3

import pytest

from testkit import Exercise

ex = Exercise(__file__)

CUSTOMERS = """customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state
c1,u1,01001,sao paulo,SP
c2,u2,20010,rio de janeiro,RJ
,u9,99999,nowhere,XX
c3,u3,30110,belo horizonte,MG
c4,u1,01001,sao paulo,SP
"""
ORDERS = """order_id,customer_id,order_status,order_purchase_timestamp,order_delivered_customer_date
o1,c1,delivered,2018-01-02 10:00:00,2018-01-10 12:00:00
o2,c2,shipped,2018-01-03 09:30:00,
o3,c9,delivered,2018-01-04 08:00:00,2018-01-12 08:00:00
o4,c3,teleported,2018-01-05 08:00:00,
o5,c4,canceled,2018-01-06 11:00:00,
"""
ITEMS = """order_id,order_item_id,product_id,seller_id,price,freight_value
o1,1,p1,s1,10.00,2.00
o1,2,p2,s1,20.00,2.00
o2,1,p1,s2,15.00,3.00
o3,1,p1,s1,9.00,1.00
o5,1,p3,s3,abc,1.00
o9,1,p1,s1,5.00,1.00
"""


@pytest.fixture(scope="module")
def pipeline():
    if ex.target.name != "starter" and not (ex.target / "pipeline.py").exists():
        pytest.skip("Bài advanced không có lời giải dạng code, xem SOLUTION.md")
    return ex.module("pipeline.py")


def make_dir(path, customers=CUSTOMERS, orders=ORDERS, items=ITEMS):
    path.mkdir()
    (path / "olist_customers_dataset.csv").write_text(customers, encoding="utf-8")
    (path / "olist_orders_dataset.csv").write_text(orders, encoding="utf-8")
    (path / "olist_order_items_dataset.csv").write_text(items, encoding="utf-8")
    return path


def q(db, sql, *params):
    with sqlite3.connect(db) as conn:
        return conn.execute(sql, params).fetchall()


def counts(db):
    return {t: q(db, f"SELECT COUNT(*) FROM {t}")[0][0] for t in ("customers", "orders", "order_items")}


def test_first_load(pipeline, tmp_path):
    data = make_dir(tmp_path / "day1")
    db = tmp_path / "olist.db"
    assert pipeline.main([str(data), "--db", str(db)]) == 0
    assert counts(db) == {"customers": 4, "orders": 3, "order_items": 3}
    assert q(db, "SELECT order_id FROM orders ORDER BY order_id") == [("o1",), ("o2",), ("o5",)]
    assert q(db, "SELECT ROUND(SUM(price), 2) FROM order_items") == [(45.0,)]
    assert q(db, "SELECT table_name, COUNT(*) FROM rejects GROUP BY 1 ORDER BY 1") == [
        ("customers", 1),
        ("order_items", 3),
        ("orders", 2),
    ]
    assert all(r[0] for r in q(db, "SELECT reason FROM rejects"))
    runs = q(db, "SELECT status, rows_loaded, rows_rejected FROM load_runs")
    assert runs == [("success", 10, 6)]


def test_foreign_keys_declared(pipeline, tmp_path):
    db = tmp_path / "olist.db"
    pipeline.main([str(make_dir(tmp_path / "d")), "--db", str(db)])
    fk_orders = {r[2] for r in q(db, "PRAGMA foreign_key_list(orders)")}
    fk_items = {r[2] for r in q(db, "PRAGMA foreign_key_list(order_items)")}
    assert fk_orders == {"customers"}
    assert fk_items == {"orders"}
    pk_items = [r[1] for r in sorted(q(db, "PRAGMA table_info(order_items)"), key=lambda r: r[5]) if r[5]]
    assert pk_items == ["order_id", "order_item_id"]


def test_rerun_is_idempotent_and_updates(pipeline, tmp_path):
    db = tmp_path / "olist.db"
    day1 = make_dir(tmp_path / "day1")
    day2 = make_dir(tmp_path / "day2", orders=ORDERS.replace("o2,c2,shipped", "o2,c2,delivered"))
    assert pipeline.main([str(day1), "--db", str(db)]) == 0
    assert pipeline.main([str(day1), "--db", str(db)]) == 0
    assert pipeline.main([str(day2), "--db", str(db)]) == 0
    assert counts(db) == {"customers": 4, "orders": 3, "order_items": 3}
    assert q(db, "SELECT order_status FROM orders WHERE order_id = 'o2'") == [("delivered",)]
    assert [r[0] for r in q(db, "SELECT status FROM load_runs ORDER BY run_id")] == ["success"] * 3


def test_failed_run_changes_nothing(pipeline, tmp_path):
    db = tmp_path / "olist.db"
    assert pipeline.main([str(make_dir(tmp_path / "ok")), "--db", str(db)]) == 0
    broken = make_dir(
        tmp_path / "broken",
        orders=ORDERS.replace("o5,c4,canceled", "o5,c4,delivered"),
        items="order_id,order_item_id,product_id,seller_id,freight_value\no1,1,p1,s1,2.00\n",
    )
    assert pipeline.main([str(broken), "--db", str(db)]) == 1
    assert q(db, "SELECT order_status FROM orders WHERE order_id = 'o5'") == [("canceled",)]
    assert counts(db) == {"customers": 4, "orders": 3, "order_items": 3}
    assert [r[0] for r in q(db, "SELECT status FROM load_runs ORDER BY run_id")] == ["success", "failed"]


def test_missing_input_dir(pipeline, tmp_path):
    assert pipeline.main([str(tmp_path / "nope"), "--db", str(tmp_path / "x.db")]) == 1
