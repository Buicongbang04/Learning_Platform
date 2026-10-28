import tempfile
import pytest
from pyspark.sql import SparkSession

from testkit import Exercise

ex = Exercise(__file__)
KEY = "spark.sql.autoBroadcastJoinThreshold"


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("06-intermediate-01")
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
    items = spark.createDataFrame(
        [(f"o{i}", f"p{i % 7}", float(10 + i % 5)) for i in range(200)],
        "order_id string, product_id string, price double",
    )
    products = spark.createDataFrame(
        [
            ("p0", "toys"),
            ("p1", "toys"),
            ("p2", "health_beauty"),
            ("p3", "health_beauty"),
            ("p4", "auto"),
            ("p5", "bed_bath_table"),
        ],
        "product_id string, product_category_name string",
    )
    return items, products


def _rows(rows):
    return sorted(tuple(r[c] for c in ("order_id", "product_id", "price", "product_category_name")) for r in rows)


def test_broadcast_join(data):
    m = ex.module("joins.py")
    joined = m.broadcast_join(*data)
    assert "BroadcastHashJoin" in m.plan_string(joined)
    assert joined.count() == 200 - len([i for i in range(200) if i % 7 == 6])


def test_sort_merge_join(spark, data):
    m = ex.module("joins.py")
    spark.conf.set(KEY, "20MB")
    rows, plan = m.sort_merge_join(spark, *data)
    assert "SortMergeJoin" in plan
    assert "BroadcastHashJoin" not in plan
    assert _rows(rows) == _rows(m.broadcast_join(*data).collect())
    assert spark.conf.get(KEY) == "20MB", "Phải khôi phục cấu hình sau khi dùng"
    spark.conf.unset(KEY)


def test_sort_merge_join_restores_conf_on_error(spark, data):
    m = ex.module("joins.py")
    items, _ = data
    spark.conf.set(KEY, "5MB")
    with pytest.raises(Exception):
        m.sort_merge_join(spark, items, items.select("order_id"))  # không có cột product_id
    assert spark.conf.get(KEY) == "5MB", "Phải khôi phục cấu hình cả khi lỗi (try/finally)"
    spark.conf.unset(KEY)


def test_revenue_by_category(data):
    m = ex.module("joins.py")
    result = m.revenue_by_category(*data)
    assert result.columns == ["product_category_name", "revenue"]
    assert "BroadcastHashJoin" in m.plan_string(result)
    expected = {}
    cats = {"p0": "toys", "p1": "toys", "p2": "health_beauty", "p3": "health_beauty", "p4": "auto", "p5": "bed_bath_table"}
    for i in range(200):
        cat = cats.get(f"p{i % 7}")
        if cat:
            expected[cat] = expected.get(cat, 0) + float(10 + i % 5)
    rows = [tuple(r) for r in result.collect()]
    assert rows == sorted(((k, round(v, 2)) for k, v in expected.items()), key=lambda kv: -kv[1])
