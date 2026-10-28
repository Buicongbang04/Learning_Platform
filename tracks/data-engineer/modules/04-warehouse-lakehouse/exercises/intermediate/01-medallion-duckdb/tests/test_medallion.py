import datetime as dt

import duckdb
import pytest

from testkit import Exercise

ex = Exercise(__file__)
RAW = ex.fixtures / "orders_raw.csv"


@pytest.fixture(scope="module")
def med():
    return ex.module("medallion.py")


@pytest.fixture
def lake(tmp_path):
    return {name: tmp_path / name for name in ("bronze", "silver", "gold")}


@pytest.fixture
def con():
    con = duckdb.connect()
    yield con
    con.close()


def test_bronze_keeps_everything(med, con, lake):
    assert med.load_bronze(con, RAW, lake["bronze"]) == 12
    rel = con.sql(f"SELECT * FROM read_parquet('{lake['bronze']}/orders.parquet')")
    types = dict(zip(rel.columns, [str(t) for t in rel.types]))
    for col in ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_value", "updated_at"]:
        assert types[col] == "VARCHAR", col
    assert "_ingested_at" in types
    files = con.execute(f"SELECT DISTINCT _source_file FROM read_parquet('{lake['bronze']}/orders.parquet')").fetchall()
    assert files == [("orders_raw.csv",)]


def test_silver_clean_and_dedup(med, con, lake):
    med.load_bronze(con, RAW, lake["bronze"])
    assert med.build_silver(con, lake["bronze"], lake["silver"]) == 7
    rel = con.sql(f"SELECT * FROM read_parquet('{lake['silver']}/orders.parquet') ORDER BY order_id")
    types = dict(zip(rel.columns, [str(t) for t in rel.types]))
    assert types["order_purchase_timestamp"] == "TIMESTAMP"
    assert types["order_value"] == "DOUBLE"
    assert types["updated_at"] == "TIMESTAMP"
    rows = {r[0]: r for r in con.execute(
        f"SELECT order_id, order_status, order_value FROM read_parquet('{lake['silver']}/orders.parquet')"
    ).fetchall()}
    assert sorted(rows) == ["o001", "o002", "o003", "o004", "o006", "o007", "o008"]
    assert rows["o002"][1] == "delivered"
    assert rows["o004"][1] == "delivered"
    assert rows["o008"][1] == "canceled"
    assert rows["o006"][2] is None


def test_gold_daily_revenue(med, con, lake):
    med.load_bronze(con, RAW, lake["bronze"])
    med.build_silver(con, lake["bronze"], lake["silver"])
    assert med.build_gold(con, lake["silver"], lake["gold"]) == 3
    rows = con.execute(
        f"SELECT order_date, delivered_orders, revenue FROM read_parquet('{lake['gold']}/daily_revenue.parquet') ORDER BY 1"
    ).fetchall()
    assert rows == [
        (dt.date(2024, 3, 1), 2, pytest.approx(200.5)),
        (dt.date(2024, 3, 2), 2, pytest.approx(200.0)),
        (dt.date(2024, 3, 3), 1, pytest.approx(60.25)),
    ]


def test_rerun_is_idempotent(med, con, lake):
    for _ in range(2):
        med.load_bronze(con, RAW, lake["bronze"])
        med.build_silver(con, lake["bronze"], lake["silver"])
        med.build_gold(con, lake["silver"], lake["gold"])
    n = con.execute(f"SELECT count(*) FROM read_parquet('{lake['bronze']}/*.parquet')").fetchone()[0]
    assert n == 12
    n = con.execute(f"SELECT count(*) FROM read_parquet('{lake['silver']}/*.parquet')").fetchone()[0]
    assert n == 7
