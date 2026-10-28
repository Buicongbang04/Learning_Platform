import tempfile
import pytest
from pyspark.sql import SparkSession

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("06-basic-01")
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
            ("o2", "c2", " Delivered ", "2018-01-15 09:30:00"),
            ("o3", "c3", "shipped", "2018-02-01 08:00:00"),
            ("o4", "c1", "DELIVERED", "2018-02-20 12:00:00"),
            ("o5", "c4", "canceled", "2018-03-05 18:00:00"),
            ("o6", "c4", "delivered", "2018-03-07 18:00:00"),
        ],
        "order_id string, customer_id string, order_status string, order_purchase_timestamp string",
    )
    customers = spark.createDataFrame(
        [("c1", "SP"), ("c2", "RJ"), ("c3", "SP"), ("c4", "MG")],
        "customer_id string, customer_state string",
    )
    payments = spark.createDataFrame(
        [
            ("o1", "credit_card", 100.0),
            ("o1", "voucher", 20.5),
            ("o2", "boleto", 80.0),
            ("o3", "credit_card", 999.0),
            ("o4", "credit_card", 30.25),
            ("o5", "credit_card", 500.0),
            ("o6", "debit_card", 140.75),
        ],
        "order_id string, payment_type string, payment_value double",
    )
    return orders, customers, payments


def test_delivered_orders(data):
    t = ex.module("transform.py")
    orders, _, _ = data
    result = t.delivered_orders(orders)
    assert sorted(r.order_id for r in result.collect()) == ["o1", "o2", "o4", "o6"]
    assert result.columns == orders.columns


def test_add_purchase_month(data):
    t = ex.module("transform.py")
    orders, _, _ = data
    rows = t.add_purchase_month(orders).select("order_id", "purchase_month").collect()
    months = {r.order_id: r.purchase_month for r in rows}
    assert months["o1"] == "2018-01"
    assert months["o3"] == "2018-02"
    assert months["o6"] == "2018-03"


def test_revenue_by_state(data):
    t = ex.module("transform.py")
    result = t.revenue_by_state(*data)
    assert result.columns == ["customer_state", "n_orders", "revenue"]
    rows = [tuple(r) for r in result.collect()]
    assert rows == [("SP", 2, 150.75), ("MG", 1, 140.75), ("RJ", 1, 80.0)]
