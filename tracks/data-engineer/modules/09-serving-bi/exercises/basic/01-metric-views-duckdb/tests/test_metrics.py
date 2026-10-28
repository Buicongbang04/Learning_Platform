import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture
def con():
    con = duckdb.connect()
    con.execute((ex.fixtures / "olist_small.sql").read_text(encoding="utf-8"))
    con.execute(ex.read("metrics.sql"))
    yield con
    con.close()


def rows(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def test_fct_order_items_excludes_canceled(con):
    data = rows(con, "SELECT * FROM fct_order_items ORDER BY order_id, product_id")
    assert len(data) == 7
    assert {r["order_id"] for r in data} == {"o1", "o2", "o3", "o5", "o6"}
    o5 = [r for r in data if r["order_id"] == "o5"][0]
    assert str(o5["order_date"]) == "2018-08-02"
    assert o5["customer_state"] == "SP"


def test_daily_revenue(con):
    data = rows(con, "SELECT * FROM metric_daily_revenue ORDER BY order_date")
    got = [(str(r["order_date"]), r["orders"], r["revenue"], r["aov"]) for r in data]
    assert got == [
        ("2018-08-01", 2, 250.0, 125.0),
        ("2018-08-02", 2, 430.0, 215.0),
        ("2018-08-03", 1, 50.0, 50.0),
    ]


def test_state_summary(con):
    data = {r["customer_state"]: r for r in rows(con, "SELECT * FROM metric_state_summary")}
    assert set(data) == {"SP", "RJ"}
    assert data["SP"]["orders"] == 3
    assert data["SP"]["revenue"] == pytest.approx(280.0)
    assert data["SP"]["aov"] == pytest.approx(93.33)
    assert data["RJ"]["aov"] == pytest.approx(225.0)
    assert data["SP"]["revenue_share"] == pytest.approx(0.3836)
    assert data["SP"]["revenue_share"] + data["RJ"]["revenue_share"] == pytest.approx(1.0)


def test_late_rate_no_fanout(con):
    data = {r["customer_state"]: r for r in rows(con, "SELECT * FROM metric_late_rate_by_state")}
    assert set(data) == {"SP", "RJ"}
    assert (data["SP"]["delivered_orders"], data["SP"]["late_orders"]) == (2, 1)
    # RJ có đơn o3 gồm 2 item: nếu join order_items, delivered_orders sẽ thành 3.
    assert (data["RJ"]["delivered_orders"], data["RJ"]["late_orders"]) == (2, 2)
    assert data["SP"]["late_rate"] == pytest.approx(0.5)
    assert data["RJ"]["late_rate"] == pytest.approx(1.0)


def test_metric_consistency(con):
    daily = con.execute("SELECT SUM(revenue), SUM(orders) FROM metric_daily_revenue").fetchone()
    state = con.execute("SELECT SUM(revenue), SUM(orders) FROM metric_state_summary").fetchone()
    fct = con.execute("SELECT SUM(price), COUNT(DISTINCT order_id) FROM fct_order_items").fetchone()
    assert daily[0] == pytest.approx(fct[0]) == pytest.approx(state[0])
    assert daily[1] == fct[1] == 5
