"""Join strategies: broadcast hash join và sort-merge join (lời giải)."""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast

THRESHOLD_KEY = "spark.sql.autoBroadcastJoinThreshold"


def plan_string(df: DataFrame) -> str:
    """Physical plan của df (đã viết sẵn)."""
    return df._jdf.queryExecution().executedPlan().toString()


def broadcast_join(items: DataFrame, products: DataFrame) -> DataFrame:
    return items.join(broadcast(products), "product_id")


def sort_merge_join(spark: SparkSession, items: DataFrame, products: DataFrame):
    old = spark.conf.get(THRESHOLD_KEY)
    spark.conf.set(THRESHOLD_KEY, "-1")
    try:
        joined = items.join(products, "product_id")
        plan = plan_string(joined)
        rows = joined.collect()
        return rows, plan
    finally:
        spark.conf.set(THRESHOLD_KEY, old)


def revenue_by_category(items: DataFrame, products: DataFrame) -> DataFrame:
    return (
        broadcast_join(items, products)
        .groupBy("product_category_name")
        .agg(F.round(F.sum("price"), 2).alias("revenue"))
        .orderBy(F.desc("revenue"))
    )
