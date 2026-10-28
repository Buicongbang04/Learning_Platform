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
def sl():
    return ex.module("semantic.py")


def test_simple_metric_by_state(con, sl):
    rows = sl.run_query(con, ["revenue", "orders"], ["customer_state"])
    assert [r["customer_state"] for r in rows] == ["RJ", "SP"]
    assert rows[0]["revenue"] == pytest.approx(450.0)
    assert rows[1]["revenue"] == pytest.approx(280.0)
    assert [r["orders"] for r in rows] == [2, 3]
    assert list(rows[0].keys()) == ["customer_state", "revenue", "orders"]


def test_ratio_metrics_without_dimensions(con, sl):
    rows = sl.run_query(con, ["aov", "late_rate", "revenue"])
    assert len(rows) == 1
    assert rows[0]["aov"] == pytest.approx(146.0)        # 730 / 5, không phải trung bình AOV từng state
    assert rows[0]["late_rate"] == pytest.approx(0.75)   # 3 trễ / 4 delivered
    assert rows[0]["revenue"] == pytest.approx(730.0)


def test_mixed_models_no_fanout(con, sl):
    rows = {r["customer_state"]: r for r in sl.run_query(con, ["items", "orders", "late_rate"], ["customer_state"])}
    assert (rows["SP"]["items"], rows["SP"]["orders"]) == (4, 3)
    assert (rows["RJ"]["items"], rows["RJ"]["orders"]) == (3, 2)
    assert rows["SP"]["late_rate"] == pytest.approx(0.5)
    assert rows["RJ"]["late_rate"] == pytest.approx(1.0)


def test_filters_and_multiple_dimensions(con, sl):
    rows = sl.run_query(con, ["revenue"], ["order_date", "customer_state"],
                        [("customer_state", "=", "RJ")])
    assert [(str(r["order_date"]), r["customer_state"], r["revenue"]) for r in rows] == [
        ("2018-08-02", "RJ", 400.0), ("2018-08-03", "RJ", 50.0)]

    rows = sl.run_query(con, ["revenue", "orders"], ["customer_state"],
                        [("order_status", "in", ["delivered"]), ("order_date", "<=", "2018-08-02")])
    got = {r["customer_state"]: (r["revenue"], r["orders"]) for r in rows}
    assert got == {"SP": (250.0, 2), "RJ": (400.0, 1)}


def test_month_dimension(con, sl):
    rows = sl.run_query(con, ["orders"], ["order_month"])
    assert len(rows) == 1
    assert str(rows[0]["order_month"]).startswith("2018-08-01")
    assert rows[0]["orders"] == 5


def test_params_not_inlined(sl):
    evil = "SP' OR '1'='1"
    sql, params = sl.compile_query(["revenue"], ["customer_state"], [("customer_state", "=", evil)])
    assert evil not in sql
    assert evil in params


def test_injected_value_matches_nothing(con, sl):
    rows = sl.run_query(con, ["revenue"], ["customer_state"], [("customer_state", "=", "SP' OR '1'='1")])
    assert rows == []


@pytest.mark.parametrize("args", [
    ([], [], []),
    (["gmv"], [], []),
    (["revenue"], ["customer_state; DROP TABLE orders"], []),
    (["revenue"], [], [("seller_id", "=", "s1")]),
    (["revenue"], [], [("customer_state", "LIKE", "S%")]),
    (["revenue"], [], [("customer_state", "in", [])]),
    (["revenue"], [], [("customer_state", "in", "SP")]),
])
def test_validation(sl, args):
    with pytest.raises(ValueError):
        sl.validate_request(*args)
    with pytest.raises(ValueError):
        sl.compile_query(*args)
