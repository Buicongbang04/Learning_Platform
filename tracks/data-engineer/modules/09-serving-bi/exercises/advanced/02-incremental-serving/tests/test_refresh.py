import datetime as dt

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

EXPECTED_SQL = """
SELECT strftime(CAST(o.order_purchase_timestamp AS DATE), '%Y-%m-%d'), c.customer_state,
       COUNT(DISTINCT o.order_id), ROUND(SUM(oi.price), 2)
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY 1, 2 ORDER BY 1, 2
"""


@pytest.fixture
def con():
    con = duckdb.connect()
    con.execute((ex.fixtures / "olist_small.sql").read_text(encoding="utf-8"))
    con.execute("""
        ALTER TABLE orders ADD COLUMN updated_at TIMESTAMP;
        UPDATE orders SET updated_at = order_purchase_timestamp;
        CREATE TABLE orders_deleted (order_id VARCHAR, order_purchase_timestamp TIMESTAMP, deleted_at TIMESTAMP);
    """)
    yield con
    con.close()


@pytest.fixture
def refresh():
    return ex.module("refresh.py")


def snapshot(con):
    return con.execute(
        "SELECT strftime(order_date, '%Y-%m-%d'), customer_state, orders, ROUND(revenue, 2) "
        "FROM agg_daily_sales ORDER BY 1, 2"
    ).fetchall()


def expected(con):
    return con.execute(EXPECTED_SQL).fetchall()


def test_first_run_is_full(con, refresh):
    assert refresh.incremental_refresh(con) == ["2018-08-01", "2018-08-02", "2018-08-03"]
    assert snapshot(con) == expected(con)


def test_no_changes_no_work(con, refresh):
    refresh.incremental_refresh(con)
    before = snapshot(con)
    assert refresh.incremental_refresh(con) == []
    assert snapshot(con) == before


def test_updates_and_new_orders(con, refresh):
    refresh.incremental_refresh(con)
    con.execute("UPDATE orders SET order_status = 'canceled', updated_at = '2018-09-01 10:00' WHERE order_id = 'o2'")
    con.execute("INSERT INTO orders VALUES ('o7', 'c2', 'delivered', '2018-08-04 09:00', '2018-08-09 10:00', "
                "'2018-08-15 00:00', '2018-09-01 11:00')")
    con.execute("INSERT INTO order_items VALUES ('o7', 1, 'p9', 's1', 70.0, 7.0)")
    assert refresh.incremental_refresh(con) == ["2018-08-01", "2018-08-04"]
    assert snapshot(con) == expected(con)


def test_hard_delete_via_tombstone(con, refresh):
    refresh.incremental_refresh(con)
    con.execute("DELETE FROM order_items WHERE order_id = 'o6'")
    con.execute("DELETE FROM orders WHERE order_id = 'o6'")
    con.execute("INSERT INTO orders_deleted VALUES ('o6', '2018-08-03 09:00', '2018-09-02 08:00')")
    assert refresh.incremental_refresh(con) == ["2018-08-03"]
    assert snapshot(con) == expected(con)
    assert not any(r[0] == "2018-08-03" for r in snapshot(con))


def test_lookback_catches_late_timestamps(con, refresh):
    refresh.incremental_refresh(con)
    con.execute("UPDATE orders SET updated_at = '2018-09-05 00:00' WHERE order_id = 'o1'")
    assert refresh.incremental_refresh(con) == ["2018-08-01"]
    # Một thay đổi tới muộn với updated_at nhỏ hơn watermark hiện tại (clock lệch, replica trễ)
    con.execute("UPDATE order_items SET price = 250.0 WHERE order_id = 'o3' AND order_item_id = 1")
    con.execute("UPDATE orders SET updated_at = '2018-09-04 23:00' WHERE order_id = 'o3'")
    assert refresh.incremental_refresh(con) == []
    assert refresh.incremental_refresh(con, lookback=dt.timedelta(hours=2)) == ["2018-08-01", "2018-08-02"]
    assert snapshot(con) == expected(con)


def test_full_rebuild_matches_and_sets_watermark(con, refresh):
    refresh.full_rebuild(con)
    assert snapshot(con) == expected(con)
    assert refresh.incremental_refresh(con) == []


def test_sequence_equals_full_rebuild(con, refresh):
    refresh.incremental_refresh(con)
    con.execute("UPDATE orders SET order_status = 'delivered', order_delivered_customer_date = '2018-08-20', "
                "updated_at = '2018-09-03 00:00' WHERE order_id = 'o5'")
    con.execute("UPDATE orders SET order_status = 'delivered', updated_at = '2018-09-03 01:00' WHERE order_id = 'o4'")
    refresh.incremental_refresh(con)
    incremental = snapshot(con)
    con.execute("DROP TABLE agg_daily_sales")
    con.execute("DROP TABLE IF EXISTS _refresh_state")
    refresh.full_rebuild(con)
    assert incremental == snapshot(con) == expected(con)
