import tempfile
import os

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("06-basic-02")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.warehouse.dir", tempfile.mkdtemp(prefix="spark-wh-"))
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="module")
def data(spark):
    orders = spark.createDataFrame(
        [
            ("o1", "c1", "delivered", "2018-01-03 10:00:00"),
            ("o2", "c2", "delivered", "2018-01-15 09:30:00"),
            ("o3", "c3", "shipped", "2018-01-20 08:00:00"),
            ("o4", "c1", "delivered", "2018-02-20 12:00:00"),
            ("o5", "c4", "delivered", "2017-12-31 23:59:00"),
        ],
        "order_id string, customer_id string, order_status string, order_purchase_timestamp string",
    )
    items = spark.createDataFrame(
        [
            ("o1", 1, "p1", "s1", 50.0, 10.0),
            ("o1", 2, "p2", "s1", 20.0, 5.5),
            ("o2", 1, "p1", "s2", 50.0, 10.0),
            ("o3", 1, "p3", "s3", 300.0, 30.0),
            ("o4", 1, "p2", "s1", 20.0, 4.25),
            ("o5", 1, "p3", "s2", 99.9, 0.1),
        ],
        "order_id string, order_item_id int, product_id string, seller_id string, "
        "price double, freight_value double",
    )
    return orders, items


def test_register_views(spark, data):
    m = ex.module("sql_parquet.py")
    m.register_views(*data)
    names = {t.name for t in spark.catalog.listTables()}
    assert {"orders", "order_items"} <= names


def test_monthly_gmv(spark, data):
    m = ex.module("sql_parquet.py")
    m.register_views(*data)
    result = m.monthly_gmv(spark)
    assert result.columns == ["month", "n_orders", "gmv"]
    rows = [tuple(r) for r in result.collect()]
    assert rows == [("2017-12", 1, 100.0), ("2018-01", 2, 145.5), ("2018-02", 1, 24.25)]
    source = ex.read("sql_parquet.py")
    assert "spark.sql(" in source


def test_write_and_read_partition(spark, data, tmp_path):
    m = ex.module("sql_parquet.py")
    orders, _ = data
    out = str(tmp_path / "orders")
    m.write_partitioned(orders, out)
    assert os.path.isdir(os.path.join(out, "year=2018", "month=1"))
    assert os.path.isdir(os.path.join(out, "year=2017", "month=12"))

    jan = m.read_month(spark, out, 2018, 1)
    assert sorted(r.order_id for r in jan.collect()) == ["o1", "o2", "o3"]
    files = {r.f for r in jan.select(F.input_file_name().alias("f")).distinct().collect()}
    assert all("year=2018/month=1/" in f for f in files), files
    # Partition pruning: điều kiện phải nằm trong PartitionFilters của FileScan
    plan = jan._jdf.queryExecution().executedPlan().toString()
    scan = [line for line in plan.splitlines() if "FileScan" in line or "PartitionFilters" in line]
    text = " ".join(scan)
    assert "PartitionFilters: [" in text and "PartitionFilters: []" not in text, plan

def test_write_overwrite_is_rerunnable(spark, data, tmp_path):
    m = ex.module("sql_parquet.py")
    orders, _ = data
    out = str(tmp_path / "orders")
    m.write_partitioned(orders, out)
    m.write_partitioned(orders, out)
    assert spark.read.parquet(out).count() == orders.count()
