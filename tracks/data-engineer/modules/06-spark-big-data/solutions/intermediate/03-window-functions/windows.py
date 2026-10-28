"""Window functions: dedup, running total, xếp hạng (lời giải)."""

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F


def latest_status(updates: DataFrame) -> DataFrame:
    w = Window.partitionBy("order_id").orderBy(F.desc("updated_at"), F.desc("order_status"))
    return (
        updates.withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )


def running_revenue(daily: DataFrame) -> DataFrame:
    w = (
        Window.partitionBy("seller_id")
        .orderBy("order_date")
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )
    return daily.withColumn("cumulative_revenue", F.round(F.sum("revenue").over(w), 2))


def top_sellers_by_state(sales: DataFrame, n: int) -> DataFrame:
    w = Window.partitionBy("seller_state").orderBy(F.desc("revenue"))
    return (
        sales.withColumn("rank", F.dense_rank().over(w))
        .filter(F.col("rank") <= n)
        .orderBy("seller_state", "rank", "seller_id")
    )
