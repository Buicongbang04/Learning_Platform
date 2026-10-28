import tempfile
import pytest
from pyspark.sql import SparkSession

from testkit import Exercise

ex = Exercise(__file__)

LINES = [
    "o1,health_beauty",
    "o2, Health_Beauty ",
    "o3,toys",
    "o4,",
    "o5,bed_bath_table",
    "o6,TOYS",
    "o7,health_beauty",
    "o8,   ",
    "o9,auto",
    "o10,bed_bath_table",
]


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("06-basic-03")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.warehouse.dir", tempfile.mkdtemp(prefix="spark-wh-"))
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_map_phase():
    m = ex.module("mapreduce.py")
    pairs = m.map_phase(LINES)
    assert len(pairs) == 8
    assert ("health_beauty", 1) in pairs
    assert all(v == 1 for _, v in pairs)
    assert all(k == k.strip().lower() and k for k, _ in pairs)


def test_shuffle_phase():
    m = ex.module("mapreduce.py")
    groups = m.shuffle_phase([("b", 1), ("a", 1), ("b", 1)])
    assert groups == {"a": [1], "b": [1, 1]}
    assert list(groups) == ["a", "b"]


def test_reduce_phase_end_to_end():
    m = ex.module("mapreduce.py")
    result = m.reduce_phase(m.shuffle_phase(m.map_phase(LINES)))
    assert result == {"auto": 1, "bed_bath_table": 2, "health_beauty": 3, "toys": 2}


def test_rdd_category_count(spark):
    m = ex.module("mapreduce.py")
    assert m.rdd_category_count(spark.sparkContext, LINES) == [
        ("auto", 1),
        ("bed_bath_table", 2),
        ("health_beauty", 3),
        ("toys", 2),
    ]


def test_top_categories(spark):
    m = ex.module("mapreduce.py")
    assert m.top_categories(spark.sparkContext, LINES, 2) == [("health_beauty", 3), ("bed_bath_table", 2)]


def test_uses_reduce_by_key():
    source = ex.read("mapreduce.py")
    assert "reduceByKey" in source
    assert "groupByKey" not in source
