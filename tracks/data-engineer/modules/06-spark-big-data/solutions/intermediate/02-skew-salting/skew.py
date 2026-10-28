"""Phát hiện data skew và xử lý bằng salting (lời giải)."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def key_distribution(df: DataFrame, key: str) -> list[tuple]:
    rows = df.groupBy(key).count().orderBy(F.desc("count"), F.asc(key)).collect()
    return [(r[key], r["count"]) for r in rows]


def partition_sizes(df: DataFrame) -> list[int]:
    rows = df.groupBy(F.spark_partition_id().alias("pid")).count().collect()
    return sorted((r["count"] for r in rows), reverse=True)


def add_salt(df: DataFrame, n_salt: int) -> DataFrame:
    # monotonically_increasing_id ổn định với cùng partitioning, chia đều theo vòng tròn
    return df.withColumn("salt", F.pmod(F.monotonically_increasing_id(), F.lit(n_salt)).cast("int"))


def salted_join(big: DataFrame, small: DataFrame, key: str, n_salt: int) -> DataFrame:
    spark = big.sparkSession
    salts = spark.range(n_salt).select(F.col("id").cast("int").alias("salt"))
    big_salted = add_salt(big, n_salt)
    small_exploded = small.crossJoin(salts)
    joined = big_salted.join(small_exploded, [key, "salt"]).drop("salt")
    return joined.select(*big.columns, *[c for c in small.columns if c != key])


def salted_count(df: DataFrame, key: str, n_salt: int) -> DataFrame:
    partial = add_salt(df, n_salt).groupBy(key, "salt").agg(F.count(F.lit(1)).alias("cnt"))
    return partial.groupBy(key).agg(F.sum("cnt").cast("long").alias("cnt"))
