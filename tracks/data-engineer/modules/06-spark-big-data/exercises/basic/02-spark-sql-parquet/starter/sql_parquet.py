"""Spark SQL trên temp view và Parquet partition."""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F  # noqa: F401


def register_views(orders: DataFrame, items: DataFrame) -> None:
    # TODO: đăng ký temp view "orders" và "order_items"
    raise NotImplementedError


def monthly_gmv(spark: SparkSession) -> DataFrame:
    # TODO: một câu spark.sql: month, n_orders, gmv (price + freight_value, round 2), chỉ delivered
    raise NotImplementedError


def write_partitioned(orders: DataFrame, path: str) -> None:
    # TODO: thêm year, month rồi ghi parquet partitionBy("year", "month"), mode overwrite
    raise NotImplementedError


def read_month(spark: SparkSession, path: str, year: int, month: int) -> DataFrame:
    # TODO: đọc parquet và lọc theo cột partition
    raise NotImplementedError
