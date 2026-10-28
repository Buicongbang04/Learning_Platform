"""Kiểm tra plan sau khi chạy tune.sql trên PostgreSQL thật. Tự skip khi chưa có PostgreSQL."""

import pytest

import testkit
from testkit import Exercise

ex = Exercise(__file__)

SETUP = """
DROP SCHEMA IF EXISTS ex_tuning CASCADE;
CREATE SCHEMA ex_tuning;
SET search_path TO ex_tuning;
CREATE TABLE orders (order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL,
    order_status TEXT NOT NULL, order_purchase_timestamp TIMESTAMPTZ NOT NULL);
INSERT INTO orders
SELECT 'o' || g, 'c' || (g % 50000),
       CASE WHEN g % 100 = 0 THEN 'processing' WHEN g % 50 = 1 THEN 'shipped' ELSE 'delivered' END,
       TIMESTAMPTZ '2018-01-01 00:00:00+00' + g * INTERVAL '2 minutes'
FROM generate_series(1, 200000) g;
CREATE TABLE order_items (order_id TEXT NOT NULL, order_item_id INT NOT NULL, seller_id TEXT NOT NULL,
    shipping_limit_date DATE NOT NULL, price NUMERIC(10, 2) NOT NULL);
INSERT INTO order_items
SELECT 'o' || g, 1, 's' || lpad((g % 3000)::text, 4, '0'), DATE '2018-01-01' + (g % 365), (g % 500) + 0.99
FROM generate_series(1, 200000) g;
CREATE TABLE order_events (order_id TEXT NOT NULL, event_type TEXT NOT NULL, event_ts TIMESTAMPTZ NOT NULL);
INSERT INTO order_events
SELECT 'o' || (g % 200000), (ARRAY['created', 'approved', 'shipped', 'delivered'])[1 + g % 4],
       TIMESTAMPTZ '2018-01-01 00:00:00+00' + (g % 364) * INTERVAL '1 day' + (g % 86400) * INTERVAL '1 second'
FROM generate_series(1, 400000) g;
ANALYZE;
"""

Q1 = ("SELECT shipping_limit_date, price FROM order_items "
      "WHERE seller_id = 's0042' AND shipping_limit_date >= DATE '2018-06-01' ORDER BY shipping_limit_date")
Q2 = ("SELECT count(*) FROM order_events "
      "WHERE event_ts >= TIMESTAMPTZ '2018-03-15 00:00:00+00' AND event_ts < TIMESTAMPTZ '2018-03-16 00:00:00+00'")
Q3 = ("SELECT order_id, order_purchase_timestamp FROM orders WHERE order_status = 'processing' "
      "ORDER BY order_purchase_timestamp DESC LIMIT 50")
QUERIES = {"q1": Q1, "q2": Q2, "q3": Q3}


def walk(node):
    yield node
    for child in node.get("Plans", []):
        yield from walk(child)


@pytest.fixture(scope="module")
def pg():
    ex.require_service("postgres")
    import psycopg

    try:
        conn = psycopg.connect(testkit.POSTGRES_DSN, autocommit=True)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Không kết nối được PostgreSQL bằng {testkit.POSTGRES_DSN}: {exc}")
    conn.execute(SETUP)
    baseline = {k: conn.execute(q).fetchall() for k, q in QUERIES.items()}
    counts = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
              for t in ("orders", "order_items", "order_events")}
    conn.execute(ex.read("tune.sql"))
    conn.execute("SET search_path TO ex_tuning")
    conn.execute("VACUUM ANALYZE")
    yield conn, baseline, counts
    conn.execute("DROP SCHEMA IF EXISTS ex_tuning CASCADE")
    conn.close()


def plan_nodes(conn, sql):
    plan = conn.execute("EXPLAIN (FORMAT JSON) " + sql).fetchone()[0][0]["Plan"]
    return list(walk(plan))


def test_data_preserved(pg):
    conn, baseline, counts = pg
    for table, n in counts.items():
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == n, table
    for key, sql in QUERIES.items():
        assert sorted(conn.execute(sql).fetchall()) == sorted(baseline[key]), key


def test_q1_index_only_no_sort(pg):
    conn, _, _ = pg
    types = [n["Node Type"] for n in plan_nodes(conn, Q1)]
    assert "Seq Scan" not in types and "Sort" not in types, types
    assert "Index Only Scan" in types, types


def test_q2_partition_pruning(pg):
    conn, _, _ = pg
    kind = conn.execute(
        "SELECT c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'ex_tuning' AND c.relname = 'order_events'"
    ).fetchone()
    assert kind and kind[0] == "p", "order_events phải là bảng partitioned"
    relations = {n["Relation Name"] for n in plan_nodes(conn, Q2) if "Relation Name" in n}
    assert len(relations) == 1, f"Plan chạm nhiều partition: {relations}"


def test_q3_no_seq_scan_no_sort(pg):
    conn, _, _ = pg
    types = [n["Node Type"] for n in plan_nodes(conn, Q3)]
    assert "Seq Scan" not in types and "Sort" not in types, types
