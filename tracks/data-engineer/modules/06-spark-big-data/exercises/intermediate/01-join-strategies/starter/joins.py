"""Join strategies: broadcast hash join và sort-merge join."""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F  # noqa: F401
from pyspark.sql.functions import broadcast  # noqa: F401

THRESHOLD_KEY = "spark.sql.autoBroadcastJoinThreshold"


def plan_string(df: DataFrame) -> str:
    """Physical plan của df (đã viết sẵn)."""
    return df._jdf.queryExecution().executedPlan().toString()


def broadcast_join(items: DataFrame, products: DataFrame) -> DataFrame:
    # TODO: inner join theo product_id, broadcast products
    raise NotImplementedError


def sort_merge_join(spark: SparkSession, items: DataFrame, products: DataFrame):
    # TODO: tắt broadcast tự động, join, lấy (rows, plan) rồi khôi phục cấu hình trong finally
    raise NotImplementedError


def revenue_by_category(items: DataFrame, products: DataFrame) -> DataFrame:
    # TODO: broadcast join rồi groupBy product_category_name, revenue = round(sum(price), 2)
    raise NotImplementedError
