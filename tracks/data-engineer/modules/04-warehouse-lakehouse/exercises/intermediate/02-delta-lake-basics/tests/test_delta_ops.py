import datetime as dt

import pyarrow as pa
import pytest
from deltalake import DeltaTable

from testkit import Exercise

ex = Exercise(__file__)

SCHEMA = pa.schema([
    ("order_id", pa.string()),
    ("order_status", pa.string()),
    ("order_value", pa.float64()),
    ("updated_at", pa.timestamp("us")),
])


def batch(rows, schema=SCHEMA):
    return pa.Table.from_pylist([dict(zip(schema.names, r)) for r in rows], schema=schema)


T0 = dt.datetime(2024, 3, 1, 10)
T1 = dt.datetime(2024, 3, 2, 10)
INITIAL = [("o1", "processing", 100.0, T0), ("o2", "shipped", 50.0, T0)]


@pytest.fixture(scope="module")
def ops():
    return ex.module("delta_ops.py")


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "orders")


def test_create_and_append(ops, path):
    assert ops.create_table(path, batch(INITIAL)) == 0
    with pytest.raises(Exception):
        ops.create_table(path, batch(INITIAL))
    assert ops.append(path, batch([("o3", "delivered", 20.0, T0)])) == 1
    assert DeltaTable(path).to_pyarrow_table().num_rows == 3


def test_append_rejects_wrong_schema(ops, path):
    ops.create_table(path, batch(INITIAL))
    bad = pa.table({"order_id": ["o9"], "order_status": ["x"], "order_value": [1.0],
                    "updated_at": pa.array([T0], pa.timestamp("us")), "extra": [1]})
    with pytest.raises(Exception):
        ops.append(path, bad)
    assert DeltaTable(path).version() == 0


def test_upsert(ops, path):
    ops.create_table(path, batch(INITIAL))
    metrics = ops.upsert(path, batch([("o1", "delivered", 100.0, T1), ("o4", "processing", 70.0, T1)]))
    assert metrics["num_target_rows_updated"] == 1
    assert metrics["num_target_rows_inserted"] == 1
    rows = {r["order_id"]: r for r in DeltaTable(path).to_pyarrow_table().to_pylist()}
    assert sorted(rows) == ["o1", "o2", "o4"]
    assert rows["o1"]["order_status"] == "delivered"
    # chạy lại cùng batch: không sinh bản trùng
    ops.upsert(path, batch([("o1", "delivered", 100.0, T1), ("o4", "processing", 70.0, T1)]))
    assert DeltaTable(path).to_pyarrow_table().num_rows == 3


def test_time_travel_and_history(ops, path):
    ops.create_table(path, batch(INITIAL))
    ops.append(path, batch([("o3", "canceled", 20.0, T0)]))
    ops.upsert(path, batch([("o1", "delivered", 100.0, T1)]))
    assert ops.delete_canceled(path) == 1
    v0 = ops.read_version(path, 0)
    assert v0.column("order_id").to_pylist() == ["o1", "o2"]
    assert v0.column("order_status").to_pylist() == ["processing", "shipped"]
    v1 = ops.read_version(path, 1)
    assert v1.column("order_id").to_pylist() == ["o1", "o2", "o3"]
    ops_list = ops.history_operations(path)
    assert len(ops_list) == 4
    assert ops_list[2:] == ["MERGE", "DELETE"]
    assert ops_list[0] in ("CREATE TABLE", "WRITE")


def test_schema_evolution(ops, path):
    ops.create_table(path, batch(INITIAL))
    schema2 = SCHEMA.append(pa.field("customer_state", pa.string()))
    v = ops.append_with_new_column(path, batch([("o5", "delivered", 10.0, T1, "SP")], schema2))
    assert v == 1
    t = DeltaTable(path).to_pyarrow_table().sort_by("order_id")
    assert "customer_state" in t.column_names
    assert t.column("customer_state").to_pylist() == [None, None, "SP"]
