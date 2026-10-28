import tempfile
import datetime as dt
import glob
import os
import shutil

import pytest
from pyspark.sql import SparkSession

from testkit import Exercise, use_solution

if use_solution():
    pytest.skip("Bài advanced chỉ có SOLUTION.md", allow_module_level=True)

ex = Exercise(__file__)
ORDERS = str(ex.fixtures / "orders.csv")
ITEMS = str(ex.fixtures / "order_items.csv")

EXPECTED = [
    (dt.date(2018, 1, 3), "s1", 2, 180.0, 2018, 1),
    (dt.date(2018, 1, 3), "s2", 1, 50.0, 2018, 1),
    (dt.date(2018, 1, 4), "s2", 1, 40.0, 2018, 1),
    (dt.date(2018, 2, 1), "s1", 1, 60.0, 2018, 2),
    (dt.date(2018, 2, 1), "s3", 1, 25.5, 2018, 2),
    (dt.date(2018, 2, 2), "s3", 1, 30.0, 2018, 2),
]
COLUMNS = ["order_date", "seller_id", "n_orders", "gmv", "year", "month"]


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("06-advanced-02")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.warehouse.dir", tempfile.mkdtemp(prefix="spark-wh-"))
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    yield session
    session.stop()


def _read(spark, path):
    rows = spark.read.parquet(path).select(*COLUMNS).collect()
    return sorted(tuple(r) for r in rows)


def test_read_raw_uses_schema(spark):
    p = ex.module("pipeline.py")
    orders, items = p.read_raw(spark, ORDERS, ITEMS)
    assert dict(orders.dtypes)["order_purchase_timestamp"] == "timestamp"
    assert dict(items.dtypes)["price"] == "double"
    assert dict(items.dtypes)["order_item_id"] == "int"
    assert orders.count() == 10 and items.count() == 12


def test_clean(spark):
    p = ex.module("pipeline.py")
    orders, items = p.clean(*p.read_raw(spark, ORDERS, ITEMS))
    assert sorted(r.order_id for r in orders.collect()) == ["o1", "o2", "o3", "o4", "o6", "o7", "o8"]
    statuses = {r.order_id: r.order_status for r in orders.collect()}
    assert statuses["o2"] == "delivered" and statuses["o8"] == "delivered"
    assert items.count() == 10
    assert items.filter("price < 0").count() == 0


def test_daily_seller_gmv(spark):
    p = ex.module("pipeline.py")
    result = p.daily_seller_gmv(*p.clean(*p.read_raw(spark, ORDERS, ITEMS)))
    assert result.columns == COLUMNS
    assert dict(result.dtypes)["year"] == "int" and dict(result.dtypes)["n_orders"] == "bigint"
    assert sorted(tuple(r) for r in result.collect()) == EXPECTED


def test_run_writes_partitions_and_is_idempotent(spark, tmp_path):
    p = ex.module("pipeline.py")
    out = str(tmp_path / "gmv")
    p.run(spark, ORDERS, ITEMS, out)
    assert os.path.isdir(os.path.join(out, "year=2018", "month=1"))
    assert os.path.isdir(os.path.join(out, "year=2018", "month=2"))
    assert _read(spark, out) == EXPECTED
    for part in ("month=1", "month=2"):
        files = glob.glob(os.path.join(out, "year=2018", part, "*.parquet"))
        assert 1 <= len(files) <= 2, f"{part} có {len(files)} file"

    p.run(spark, ORDERS, ITEMS, out)
    assert _read(spark, out) == EXPECTED, "Chạy lại không được nhân đôi dữ liệu"


def test_backfill_one_month_keeps_others(spark, tmp_path):
    p = ex.module("pipeline.py")
    out = str(tmp_path / "gmv")
    p.run(spark, ORDERS, ITEMS, out)

    # Dữ liệu nguồn thay đổi ở cả tháng 1 và tháng 2, nhưng chỉ backfill tháng 2
    items2 = tmp_path / "order_items.csv"
    shutil.copy(ITEMS, items2)
    text = items2.read_text().replace("o8,1,p4,s3,30.00", "o8,1,p4,s3,35.00").replace(
        "o1,1,p1,s1,100.00", "o1,1,p1,s1,999.00"
    )
    items2.write_text(text + "o6,3,p5,s3,10.00,1.00\n")

    p.run(spark, ORDERS, str(items2), out, year=2018, month=2)
    expected = [r for r in EXPECTED if r[5] == 1] + [
        (dt.date(2018, 2, 1), "s1", 1, 60.0, 2018, 2),
        (dt.date(2018, 2, 1), "s3", 1, 35.5, 2018, 2),
        (dt.date(2018, 2, 2), "s3", 1, 35.0, 2018, 2),
    ]
    assert _read(spark, out) == sorted(expected)

    p.run(spark, ORDERS, str(items2), out, year=2018, month=2)
    assert _read(spark, out) == sorted(expected), "Backfill chạy lại phải idempotent"
