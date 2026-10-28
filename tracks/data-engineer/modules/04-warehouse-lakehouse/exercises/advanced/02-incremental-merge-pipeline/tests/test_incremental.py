import datetime as dt

import duckdb
import pyarrow as pa
import pytest
from deltalake import DeltaTable

from testkit import Exercise, use_solution

if use_solution():
    pytest.skip("Bài advanced không có lời giải chạy được; xem SOLUTION.md", allow_module_level=True)

ex = Exercise(__file__)

SCHEMA = pa.schema([
    ("order_id", pa.string()),
    ("customer_state", pa.string()),
    ("order_status", pa.string()),
    ("order_purchase_timestamp", pa.timestamp("us")),
    ("order_value", pa.float64()),
    ("updated_at", pa.timestamp("us")),
])
D1, D2, D3 = dt.date(2024, 3, 1), dt.date(2024, 3, 2), dt.date(2024, 3, 3)


def ts(day, hour):
    return dt.datetime(2024, 3, day, hour)


def batch(rows):
    return pa.Table.from_pylist([dict(zip(SCHEMA.names, r)) for r in rows], schema=SCHEMA)


B1 = batch([
    ("o1", "SP", "delivered", ts(1, 9), 100.0, ts(1, 9)),
    ("o2", "RJ", "processing", ts(1, 10), 50.0, ts(1, 10)),
    ("o3", "SP", "delivered", ts(2, 8), 70.0, ts(2, 8)),
    ("o4", "MG", "delivered", ts(3, 8), 30.0, ts(3, 8)),
])
B2 = batch([
    ("o2", "RJ", "shipped", ts(1, 10), 50.0, ts(2, 9)),
    ("o2", "RJ", "delivered", ts(1, 10), 50.0, ts(4, 9)),   # cùng batch, bản mới hơn thắng
    ("o5", "SP", "delivered", ts(3, 12), 20.0, ts(3, 12)),
])
B_STALE = batch([
    ("o2", "RJ", "processing", ts(1, 10), 50.0, ts(1, 11)),  # cũ hơn bản delivered
])
B_LATE = batch([
    ("o3", "SP", "canceled", ts(2, 8), 70.0, ts(5, 8)),       # ngày cũ, đến trễ
])


@pytest.fixture(scope="module")
def inc():
    return ex.module("incremental.py")


@pytest.fixture
def paths(tmp_path):
    return str(tmp_path / "silver"), str(tmp_path / "gold")


def silver_state(path):
    t = DeltaTable(path).to_pyarrow_table()
    return sorted((r["order_id"], r["order_status"], r["updated_at"]) for r in t.to_pylist())


def gold_state(path):
    t = DeltaTable(path).to_pyarrow_table()
    return {r["order_date"]: (r["delivered_orders"], pytest.approx(r["revenue"])) for r in t.to_pylist()}


def full_recompute(silver_path):
    con = duckdb.connect()
    con.register("silver", DeltaTable(silver_path).to_pyarrow_table())
    rows = con.execute(
        """SELECT CAST(order_purchase_timestamp AS DATE), COUNT(*), SUM(order_value)
           FROM silver WHERE order_status = 'delivered' GROUP BY 1"""
    ).fetchall()
    return {d: (n, pytest.approx(r)) for d, n, r in rows}


def test_first_batch(inc, paths):
    silver, gold = paths
    assert inc.run_batch(silver, gold, B1) == {D1, D2, D3}
    assert len(silver_state(silver)) == 4
    assert gold_state(gold) == {D1: (1, 100.0), D2: (1, 70.0), D3: (1, 30.0)}


def test_rerun_same_batch_is_noop(inc, paths):
    silver, gold = paths
    inc.run_batch(silver, gold, B1)
    before_s, before_g = silver_state(silver), gold_state(gold)
    assert inc.run_batch(silver, gold, B1) == set()
    assert silver_state(silver) == before_s
    assert gold_state(gold) == before_g


def test_in_batch_duplicates_and_stale(inc, paths):
    silver, gold = paths
    inc.run_batch(silver, gold, B1)
    assert inc.run_batch(silver, gold, B2) == {D1, D3}
    status = {r[0]: r[1] for r in silver_state(silver)}
    assert status["o2"] == "delivered"
    assert inc.run_batch(silver, gold, B_STALE) == set()
    assert {r[0]: r[1] for r in silver_state(silver)}["o2"] == "delivered"
    assert gold_state(gold) == full_recompute(silver)


def test_late_data_old_day(inc, paths):
    silver, gold = paths
    for b in (B1, B2):
        inc.run_batch(silver, gold, b)
    assert inc.run_batch(silver, gold, B_LATE) == {D2}
    g = gold_state(gold)
    assert D2 not in g  # o3 bị huỷ, ngày 2 không còn đơn delivered
    assert g == full_recompute(silver)


def test_refresh_gold_only_touches_given_dates(inc, paths):
    silver, gold = paths
    inc.run_batch(silver, gold, B1)
    # đổi silver ở cả D1 và D3, nhưng chỉ refresh D1
    inc.load_increment(silver, B2)
    inc.refresh_gold(silver, gold, {D1})
    g = gold_state(gold)
    assert g[D1] == (2, pytest.approx(150.0))
    assert g[D3] == (1, pytest.approx(30.0))  # chưa refresh nên giữ số cũ
    assert inc.refresh_gold(silver, gold, set()) == 0
    inc.refresh_gold(silver, gold, {D3})
    assert gold_state(gold) == full_recompute(silver)
