"""Spark SQL trên temp view và Parquet partition (lời giải)."""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def register_views(orders: DataFrame, items: DataFrame) -> None:
    orders.createOrReplaceTempView("orders")
    items.createOrReplaceTempView("order_items")


def monthly_gmv(spark: SparkSession) -> DataFrame:
    return spark.sql(
        """
        SELECT
            date_format(to_timestamp(o.order_purchase_timestamp), 'yyyy-MM') AS month,
            COUNT(DISTINCT o.order_id)                                       AS n_orders,
            ROUND(SUM(i.price + i.freight_value), 2)                         AS gmv
        FROM orders o
        JOIN order_items i ON i.order_id = o.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY 1
        ORDER BY month
        """
    )


def write_partitioned(orders: DataFrame, path: str) -> None:
    ts = F.to_timestamp("order_purchase_timestamp")
    (
        orders.withColumn("year", F.year(ts))
        .withColumn("month", F.month(ts))
        .repartition("year", "month")  # mỗi thư mục một file, tránh small files
        .write.mode("overwrite")
        .partitionBy("year", "month")
        .parquet(path)
    )


def read_month(spark: SparkSession, path: str, year: int, month: int) -> DataFrame:
    return spark.read.parquet(path).filter((F.col("year") == year) & (F.col("month") == month))
