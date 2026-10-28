import os
import re

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

EXTRA = """
CREATE TABLE run_context AS SELECT DATE '2018-08-30' AS as_of;
INSERT INTO customers VALUES ('c8', 'u8', 'PR'), ('c9', 'u9', 'SP');
INSERT INTO orders VALUES
    ('o8', 'c8', 'processing', '2018-08-04 10:00:00', NULL, '2018-08-28 00:00:00'),
    ('o9', 'c9', 'shipped',    '2018-08-04 12:00:00', NULL, '2018-09-05 00:00:00');
INSERT INTO order_items VALUES
    ('o8', 1, 'p5', 's3', 60.0, 9.0),
    ('o8', 2, 'p6', 's1', 40.0, 4.0),
    ('o9', 1, 'p1', 's1', 100.0, 11.0);
"""


@pytest.fixture
def con():
    con = duckdb.connect()
    con.execute((ex.fixtures / "olist_small.sql").read_text(encoding="utf-8"))
    con.execute(EXTRA)
    con.execute(ex.read("marts.sql"))
    yield con
    con.close()


def rows(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def test_mart_ops_daily(con):
    data = {str(r["order_date"]): r for r in rows(con, "SELECT * FROM mart_ops_daily")}
    assert set(data) == {"2018-08-01", "2018-08-02", "2018-08-03", "2018-08-04"}
    d1 = data["2018-08-01"]
    assert (d1["orders"], d1["delivered_orders"], d1["late_orders"]) == (2, 2, 1)
    assert d1["late_rate"] == pytest.approx(0.5)
    assert d1["revenue"] == pytest.approx(250.0)
    assert data["2018-08-04"]["late_rate"] is None
    assert data["2018-08-04"]["revenue"] == pytest.approx(200.0)
    assert all(r["updated_at"] is not None for r in data.values())
    total = con.execute("SELECT SUM(revenue), SUM(orders) FROM mart_ops_daily").fetchone()
    assert total[0] == pytest.approx(930.0) and total[1] == 7


def test_mart_overdue_orders(con):
    data = {r["order_id"]: r for r in rows(con, "SELECT * FROM mart_overdue_orders")}
    assert set(data) == {"o5", "o8"}
    assert data["o5"]["days_overdue"] == 5
    assert data["o8"]["days_overdue"] == 2
    assert data["o8"]["seller_ids"] == "s1,s3"
    assert data["o8"]["customer_state"] == "PR"


def test_mart_seller_late_rate(con):
    data = {r["seller_id"]: r for r in rows(con, "SELECT * FROM mart_seller_late_rate")}
    assert (data["s1"]["delivered_orders"], data["s1"]["late_orders"]) == (2, 1)
    assert (data["s2"]["delivered_orders"], data["s2"]["late_orders"]) == (3, 2)
    assert data["s2"]["late_rate"] == pytest.approx(2 / 3, abs=1e-4)
    assert "s3" not in data or data["s3"]["delivered_orders"] == 0


def test_dashboard_spec(con):
    spec = ex.module("dashboard.py").dashboard_spec()
    cards = spec["cards"]
    assert spec["name"] and len(cards) >= 4
    assert sum(1 for c in cards if c["row"] == 0 and c["display"] == "scalar") >= 2
    assert any(c["display"] == "line" for c in cards)
    assert any(c["display"] == "table" and "mart_overdue_orders" in c["sql"] for c in cards)

    occupied = set()
    for c in cards:
        assert 0 <= c["col"] and c["col"] + c["size_x"] <= 24, c["name"]
        assert c["size_x"] > 0 and c["size_y"] > 0
        cells = {(r, k) for r in range(c["row"], c["row"] + c["size_y"])
                 for k in range(c["col"], c["col"] + c["size_x"])}
        assert not (cells & occupied), f"Card chồng nhau: {c['name']}"
        occupied |= cells

        tables = set(re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", c["sql"], flags=re.I))
        assert tables and all(t.lower().startswith("mart_") for t in tables), (c["name"], tables)
        con.execute(c["sql"]).fetchall()  # SQL chạy được trên các mart


def test_publish_to_metabase():
    ex.require_service("metabase")
    user, password = os.environ.get("METABASE_USER"), os.environ.get("METABASE_PASSWORD")
    if not user or not password:
        pytest.skip("Đặt METABASE_USER, METABASE_PASSWORD (và METABASE_DB_ID) để test publish")
    dash = ex.module("dashboard.py")
    db_id = int(os.environ.get("METABASE_DB_ID", "1"))
    first = dash.publish(dash.dashboard_spec(), "http://localhost:3000", user, password, db_id)
    second = dash.publish(dash.dashboard_spec(), "http://localhost:3000", user, password, db_id)
    assert isinstance(first, int) and first == second
