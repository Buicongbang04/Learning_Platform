import tempfile
import uuid

import pytest
from pyspark.sql import SparkSession

from testkit import Exercise, use_solution

if use_solution():
    pytest.skip("Bài advanced chỉ có SOLUTION.md", allow_module_level=True)

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("06-advanced-01")
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
        [(f"o{i}", "canceled" if i % 10 == 0 else "delivered") for i in range(60)],
        "order_id string, order_status string",
    )
    item_rows = []
    for i in range(60):
        item_rows.append((f"o{i}", 1, "s1", 50.0))          # s1: gold
        if i % 3 == 0:
            item_rows.append((f"o{i}", 2, "s2", 15.0))      # s2: silver
        if i < 4:
            item_rows.append((f"o{i}", 3, "s3", 12.5))      # s3: bronze
    item_rows.append(("o10", 1, "s4", 999.0))               # s4: chỉ có đơn canceled -> bị loại
    items = spark.createDataFrame(item_rows, "order_id string, order_item_id int, seller_id string, price double")
    sellers = spark.createDataFrame(
        [("s1", "SP"), ("s2", "RJ"), ("s3", "MG"), ("s4", "SP"), ("s5", "PR")],
        "seller_id string, seller_state string",
    )
    return orders, items, sellers


def _expected():
    delivered = {f"o{i}" for i in range(60) if i % 10 != 0}
    stats = {}
    for i in range(60):
        o = f"o{i}"
        if o not in delivered:
            continue
        for sid, price, ok in (("s1", 50.0, True), ("s2", 15.0, i % 3 == 0), ("s3", 12.5, i < 4)):
            if ok:
                n, g = stats.get(sid, (0, 0.0))
                stats[sid] = (n + 1, g + price)
    state = {"s1": "SP", "s2": "RJ", "s3": "MG"}
    rows = []
    for sid, (n, g) in stats.items():
        g = round(g, 2)
        tier = "gold" if g >= 1000 else "silver" if g >= 200 else "bronze"
        rows.append((sid, state[sid], n, g, round(g / n, 2), tier))
    return sorted(rows, key=lambda r: (-r[3], r[0]))


def _jobs_during(spark, fn):
    sc = spark.sparkContext
    group = f"probe-{uuid.uuid4().hex}"
    sc.setJobGroup(group, "đếm số job")
    try:
        result = fn()
    finally:
        sc.setLocalProperty("spark.jobGroup.id", None)
    return result, len(sc.statusTracker().getJobIdsForGroup(group))


def test_report_is_correct(spark, data):
    job = ex.module("job.py")
    report = job.seller_report(spark, *data)
    assert report.columns == ["seller_id", "seller_state", "n_orders", "gmv", "avg_ticket", "tier"]
    assert [tuple(r) for r in report.collect()] == _expected()


def test_report_is_lazy(spark, data):
    job = ex.module("job.py")
    _, n_jobs = _jobs_during(spark, lambda: job.seller_report(spark, *data))
    assert n_jobs == 0, f"seller_report đã chạy {n_jobs} Spark job; hàm chỉ nên dựng plan"


def test_no_python_udf(spark, data):
    job = ex.module("job.py")
    report = job.seller_report(spark, *data)
    plan = report._jdf.queryExecution().executedPlan().toString()
    assert "BatchEvalPython" not in plan and "ArrowEvalPython" not in plan, plan


def test_tier_counts_single_action(spark, data):
    job = ex.module("job.py")
    report = job.seller_report(spark, *data)
    # Với AQE và broadcast, một action có thể sinh vài Spark job. Lấy mốc là số job của MỘT action
    # groupBy + collect trên cùng report; tier_counts không được tốn hơn mốc đó.
    _, baseline = _jobs_during(spark, lambda: report.groupBy("tier").count().collect())
    counts, n_jobs = _jobs_during(spark, lambda: job.tier_counts(report))
    assert counts == {"gold": 1, "silver": 1, "bronze": 1}
    assert n_jobs <= baseline, f"tier_counts chạy {n_jobs} job, một action chỉ cần {baseline}"
