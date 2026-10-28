import tempfile
import datetime as dt

import pytest
from pyspark.sql import SparkSession

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("06-intermediate-03")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.warehouse.dir", tempfile.mkdtemp(prefix="spark-wh-"))
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    yield session
    session.stop()


def ts(day, hour=0):
    return dt.datetime(2018, 1, day, hour)


def test_latest_status(spark):
    m = ex.module("windows.py")
    updates = spark.createDataFrame(
        [
            ("o1", "created", ts(1)),
            ("o1", "approved", ts(1, 5)),
            ("o1", "shipped", ts(3)),
            ("o2", "created", ts(2)),
            ("o3", "created", ts(4)),
            ("o3", "canceled", ts(5)),
            ("o3", "approved", ts(5)),
        ],
        "order_id string, order_status string, updated_at timestamp",
    )
    result = m.latest_status(updates)
    assert result.columns == updates.columns
    got = {r.order_id: (r.order_status, r.updated_at) for r in result.collect()}
    assert got == {"o1": ("shipped", ts(3)), "o2": ("created", ts(2)), "o3": ("canceled", ts(5))}
    assert result.count() == 3
    assert "row_number" in ex.read("windows.py")


def test_running_revenue(spark):
    m = ex.module("windows.py")
    daily = spark.createDataFrame(
        [
            ("s1", dt.date(2018, 1, 3), 30.0),
            ("s1", dt.date(2018, 1, 1), 10.0),
            ("s1", dt.date(2018, 1, 2), 20.5),
            ("s2", dt.date(2018, 1, 1), 5.25),
            ("s2", dt.date(2018, 1, 5), 4.75),
        ],
        "seller_id string, order_date date, revenue double",
    )
    result = m.running_revenue(daily)
    assert "cumulative_revenue" in result.columns
    got = {(r.seller_id, r.order_date.day): r.cumulative_revenue for r in result.collect()}
    assert got == {("s1", 1): 10.0, ("s1", 2): 30.5, ("s1", 3): 60.5, ("s2", 1): 5.25, ("s2", 5): 10.0}


def test_top_sellers_by_state(spark):
    m = ex.module("windows.py")
    sales = spark.createDataFrame(
        [
            ("a", "SP", 100.0),
            ("b", "SP", 100.0),
            ("c", "SP", 80.0),
            ("d", "SP", 50.0),
            ("e", "RJ", 70.0),
            ("f", "RJ", 90.0),
            ("g", "MG", 10.0),
        ],
        "seller_id string, seller_state string, revenue double",
    )
    result = m.top_sellers_by_state(sales, 2)
    rows = [(r.seller_state, r["rank"], r.seller_id) for r in result.collect()]
    assert rows == [
        ("MG", 1, "g"),
        ("RJ", 1, "f"),
        ("RJ", 2, "e"),
        ("SP", 1, "a"),
        ("SP", 1, "b"),
        ("SP", 2, "c"),
    ]
