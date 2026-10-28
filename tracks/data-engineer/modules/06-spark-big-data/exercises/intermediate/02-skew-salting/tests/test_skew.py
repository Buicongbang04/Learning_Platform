import tempfile
import pytest
from pyspark.sql import SparkSession

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("06-intermediate-02")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.warehouse.dir", tempfile.mkdtemp(prefix="spark-wh-"))
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.adaptive.enabled", "false")  # để thấy rõ skew, không cho AQE gộp/tách partition
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="module")
def data(spark):
    rows = [(f"o{i}", "s_hot", float(i % 50)) for i in range(800)]
    rows += [(f"x{i}", f"s{i % 10}", float(i)) for i in range(100)]
    big = spark.createDataFrame(rows, "order_id string, seller_id string, price double").repartition(3)
    sellers = spark.createDataFrame(
        [("s_hot", "SP")] + [(f"s{i}", "RJ" if i % 2 else "MG") for i in range(10)],
        "seller_id string, seller_state string",
    )
    return big, sellers


def test_key_distribution(data):
    m = ex.module("skew.py")
    big, _ = data
    dist = m.key_distribution(big, "seller_id")
    assert dist[0] == ("s_hot", 800)
    assert dist[1] == ("s0", 10)
    assert len(dist) == 11


def test_partition_sizes_show_skew(data):
    m = ex.module("skew.py")
    big, _ = data
    sizes = m.partition_sizes(big.repartition(4, "seller_id"))
    assert sum(sizes) == 900
    assert sizes == sorted(sizes, reverse=True)
    assert sizes[0] >= 800


def test_add_salt_spreads_hot_key(data):
    m = ex.module("skew.py")
    big, _ = data
    salted = m.add_salt(big, 8)
    assert "salt" in salted.columns
    values = {r.salt for r in salted.select("salt").distinct().collect()}
    assert values <= set(range(8)) and len(values) >= 6
    assert dict(salted.dtypes)["salt"] == "int"
    sizes = m.partition_sizes(salted.repartition(4, "seller_id", "salt"))
    assert sum(sizes) == 900
    assert sizes[0] < 600


def test_salted_join_equals_plain_join(data):
    m = ex.module("skew.py")
    big, sellers = data
    plain = big.join(sellers, "seller_id")
    salted = m.salted_join(big, sellers, "seller_id", 8)
    assert salted.columns == big.columns + ["seller_state"]
    assert sorted(salted.collect()) == sorted(plain.select(*salted.columns).collect())


def test_salted_count_equals_plain_count(data):
    m = ex.module("skew.py")
    big, _ = data
    result = m.salted_count(big, "seller_id", 8)
    assert result.columns == ["seller_id", "cnt"]
    got = {r.seller_id: r.cnt for r in result.collect()}
    expected = {r.seller_id: r["count"] for r in big.groupBy("seller_id").count().collect()}
    assert got == expected
