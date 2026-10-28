import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture
def con():
    con = duckdb.connect()
    con.execute((ex.fixtures / "olist_small.sql").read_text(encoding="utf-8"))
    yield con
    con.close()


@pytest.fixture
def agg():
    return ex.module("aggregate.py")


def table(con):
    return [
        (str(r[0]), r[1], r[2], r[3], round(r[4], 2), round(r[5], 2))
        for r in con.execute(
            "SELECT order_date, customer_state, orders, items, revenue, freight "
            "FROM agg_daily_sales ORDER BY 1, 2"
        ).fetchall()
    ]


EXPECTED = [
    ("2018-08-01", "SP", 2, 3, 250.0, 27.0),
    ("2018-08-02", "RJ", 1, 2, 400.0, 40.0),
    ("2018-08-02", "SP", 1, 1, 30.0, 8.0),
    ("2018-08-03", "RJ", 1, 1, 50.0, 6.0),
]


def test_build_values(con, agg):
    n = agg.build_agg_daily_sales(con, "2018-08-01", "2018-08-31")
    assert n == 4
    assert table(con) == EXPECTED


def test_idempotent_and_partial_range(con, agg):
    agg.build_agg_daily_sales(con, "2018-08-01", "2018-08-01")
    assert table(con) == EXPECTED[:1]
    agg.build_agg_daily_sales(con, "2018-08-02", "2018-08-03")
    agg.build_agg_daily_sales(con, "2018-08-02", "2018-08-03")
    assert table(con) == EXPECTED


def test_reconcile_ok(con, agg):
    agg.build_agg_daily_sales(con, "2018-08-01", "2018-08-31")
    res = agg.reconcile(con, "2018-08-01", "2018-08-31")
    assert res["ok"] is True
    assert res["mismatched_dates"] == []
    assert res["agg_revenue"] == pytest.approx(730.0)
    assert res["src_revenue"] == pytest.approx(730.0)
    assert res["agg_orders"] == res["src_orders"] == 5


def test_reconcile_detects_tampering(con, agg):
    agg.build_agg_daily_sales(con, "2018-08-01", "2018-08-31")
    con.execute("UPDATE agg_daily_sales SET revenue = revenue + 5 WHERE order_date = DATE '2018-08-01'")
    res = agg.reconcile(con, "2018-08-01", "2018-08-31")
    assert res["ok"] is False
    assert res["mismatched_dates"] == ["2018-08-01"]


def test_tolerance(con, agg):
    agg.build_agg_daily_sales(con, "2018-08-01", "2018-08-31")
    con.execute("UPDATE agg_daily_sales SET revenue = revenue + 0.001 WHERE order_date = DATE '2018-08-02'")
    assert agg.reconcile(con, "2018-08-01", "2018-08-31")["ok"] is True


def test_late_arriving_data(con, agg):
    agg.build_agg_daily_sales(con, "2018-08-01", "2018-08-31")
    con.execute("INSERT INTO orders VALUES ('o7', 'c2', 'delivered', '2018-08-04 10:00:00', "
                "'2018-08-09 10:00:00', '2018-08-15 00:00:00')")
    con.execute("INSERT INTO order_items VALUES ('o7', 1, 'p9', 's1', 70.0, 7.0)")
    res = agg.reconcile(con, "2018-08-01", "2018-08-31")
    assert res["ok"] is False
    assert res["mismatched_dates"] == ["2018-08-04"]
    agg.build_agg_daily_sales(con, "2018-08-04", "2018-08-04")
    res = agg.reconcile(con, "2018-08-01", "2018-08-31")
    assert res["ok"] is True
    assert res["src_orders"] == 6
