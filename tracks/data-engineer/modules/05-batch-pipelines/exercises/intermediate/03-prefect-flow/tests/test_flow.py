"""Chạy flow Prefect thật ở local, trên một Prefect server tạm (prefect_test_harness)."""

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)

CSV = """order_id,order_status,order_purchase_timestamp,amount
o1,delivered,2018-01-01 10:00:00,10
o2, Shipped ,2018-01-01 11:00:00,20
o2,delivered,2018-01-01 11:00:00,25
o3,delivered,2018-01-02 09:00:00,30
o4,canceled,2018-01-03 09:00:00,40
"""


@pytest.fixture(scope="module", autouse=True)
def prefect_harness():
    from prefect.testing.utilities import prefect_test_harness

    with prefect_test_harness(server_startup_timeout=120):
        yield


@pytest.fixture
def paths(tmp_path):
    src = tmp_path / "orders.csv"
    src.write_text(CSV, encoding="utf-8")
    return str(src), str(tmp_path / "wh.duckdb")


def table(db):
    con = duckdb.connect(db)
    try:
        return con.execute(
            "SELECT order_id, order_status, amount, CAST(ds AS VARCHAR) FROM daily_orders ORDER BY ds, order_id"
        ).fetchall()
    finally:
        con.close()


def test_objects_are_prefect_tasks_and_flows():
    from prefect import Flow, Task

    m = ex.module("flow.py")
    for name in ["extract", "transform", "load"]:
        assert isinstance(getattr(m, name), Task), f"{name} phải là @task"
    assert isinstance(m.olist_daily, Flow) and m.olist_daily.name == "olist-daily"
    assert isinstance(m.backfill, Flow) and m.backfill.name == "olist-backfill"
    assert m.extract.retries >= 3


def test_transform_logic():
    m = ex.module("flow.py")
    rows = [
        {"order_id": "o2", "order_status": " Shipped ", "amount": "20"},
        {"order_id": "o1", "order_status": "DELIVERED", "amount": "10"},
        {"order_id": "o2", "order_status": "delivered", "amount": "25"},
    ]
    assert m.transform.fn(rows) == [("o1", "delivered", 10.0), ("o2", "delivered", 25.0)]


def test_flow_retries_flaky_source_and_is_idempotent(paths, monkeypatch):
    m = ex.module("flow.py")
    src, db = paths
    real = m.fetch_rows
    calls = {"n": 0}

    def flaky(path):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise ConnectionError("API tạm thời lỗi")
        return real(path)

    monkeypatch.setattr(m, "fetch_rows", flaky)
    assert m.olist_daily(src, db, "2018-01-01") == {"ds": "2018-01-01", "rows": 2}
    assert calls["n"] == 3
    m.olist_daily(src, db, "2018-01-01")
    assert table(db) == [("o1", "delivered", 10.0, "2018-01-01"), ("o2", "delivered", 25.0, "2018-01-01")]


def test_backfill_runs_each_day(paths):
    m = ex.module("flow.py")
    src, db = paths
    out = m.backfill(src, db, "2018-01-01", "2018-01-03")
    assert out == [
        {"ds": "2018-01-01", "rows": 2},
        {"ds": "2018-01-02", "rows": 1},
        {"ds": "2018-01-03", "rows": 1},
    ]
    m.backfill(src, db, "2018-01-02", "2018-01-03")  # chạy lại một phần
    assert len(table(db)) == 4
