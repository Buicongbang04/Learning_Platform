import duckdb
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

CSV = """order_id,customer_id,order_status,order_purchase_timestamp,amount
o1,c1,delivered,2018-01-01 10:00:00,100.5
o2,c2, DELIVERED ,2018-01-01 11:30:00,50
o3,c3,canceled,2018-01-02 09:00:00,70
o2,c2,Shipped,2018-01-01 11:30:00,55
,c4,delivered,2018-01-01 12:00:00,10
o4,c1,delivered,2018-01-02 12:00:00,30
"""


@pytest.fixture
def csv_path(tmp_path):
    path = tmp_path / "orders.csv"
    path.write_text(CSV, encoding="utf-8")
    return str(path)


def count(con, ds=None):
    if ds is None:
        return con.execute("SELECT count(*) FROM fct_orders").fetchone()[0]
    return con.execute("SELECT count(*) FROM fct_orders WHERE ds = CAST(? AS DATE)", [ds]).fetchone()[0]


def test_extract_keeps_strings(csv_path):
    p = ex.module("pipeline.py")
    df = p.extract(csv_path)
    assert len(df) == 6
    assert all(pd.api.types.is_string_dtype(df[c]) or df[c].dtype == object for c in df.columns)
    assert df.loc[0, "amount"] == "100.5"


def test_transform_rules(csv_path):
    p = ex.module("pipeline.py")
    out = p.transform(p.extract(csv_path), "2018-01-01")
    assert list(out.columns) == ["order_id", "customer_id", "order_status", "amount", "ds"]
    assert list(out["order_id"]) == ["o1", "o2"]
    assert list(out.index) == [0, 1]
    row = out[out["order_id"] == "o2"].iloc[0]
    assert row["order_status"] == "shipped"  # bản sau cùng
    assert row["amount"] == pytest.approx(55.0)
    assert out["amount"].dtype == float
    assert set(out["ds"]) == {"2018-01-01"}


def test_load_is_idempotent(csv_path):
    p = ex.module("pipeline.py")
    con = duckdb.connect()
    df = p.transform(p.extract(csv_path), "2018-01-01")
    assert p.load(con, df, "2018-01-01") == 2
    assert p.load(con, df, "2018-01-01") == 2
    assert count(con, "2018-01-01") == 2


def test_reload_replaces_only_its_partition(csv_path):
    p = ex.module("pipeline.py")
    con = duckdb.connect()
    raw = p.extract(csv_path)
    p.load(con, p.transform(raw, "2018-01-01"), "2018-01-01")
    p.load(con, p.transform(raw, "2018-01-02"), "2018-01-02")
    fixed = pd.DataFrame(
        {"order_id": ["o9"], "customer_id": ["c9"], "order_status": ["delivered"], "amount": [1.0], "ds": ["2018-01-01"]}
    )
    p.load(con, fixed, "2018-01-01")
    assert con.execute(
        "SELECT order_id FROM fct_orders WHERE ds = DATE '2018-01-01'"
    ).fetchall() == [("o9",)]
    assert count(con, "2018-01-02") == 2


def test_failed_insert_keeps_old_partition(csv_path):
    p = ex.module("pipeline.py")
    con = duckdb.connect()
    p.load(con, p.transform(p.extract(csv_path), "2018-01-01"), "2018-01-01")
    broken = pd.DataFrame({"order_id": ["x"]})  # thiếu cột -> INSERT lỗi
    with pytest.raises(Exception):
        p.load(con, broken, "2018-01-01")
    assert count(con, "2018-01-01") == 2


def test_run_end_to_end(csv_path, tmp_path):
    p = ex.module("pipeline.py")
    db = str(tmp_path / "wh.duckdb")
    assert p.run(csv_path, db, "2018-01-02") == 2
    assert p.run(csv_path, db, "2018-01-02") == 2
    assert p.run(csv_path, db, "2018-01-01") == 2
    con = duckdb.connect(db)
    assert count(con) == 4
    total = con.execute("SELECT sum(amount) FROM fct_orders").fetchone()[0]
    assert total == pytest.approx(100.5 + 55 + 70 + 30)
