"""Window functions: dedup, running total, xếp hạng."""

from pyspark.sql import DataFrame, Window  # noqa: F401
from pyspark.sql import functions as F  # noqa: F401


def latest_status(updates: DataFrame) -> DataFrame:
    # TODO: row_number theo order_id, updated_at giảm dần (hoà: order_status giảm dần), giữ rn == 1
    raise NotImplementedError


def running_revenue(daily: DataFrame) -> DataFrame:
    # TODO: thêm cumulative_revenue = sum(revenue) từ đầu tới dòng hiện tại theo seller, round 2
    raise NotImplementedError


def top_sellers_by_state(sales: DataFrame, n: int) -> DataFrame:
    # TODO: dense_rank theo revenue giảm dần trong seller_state, giữ rank <= n
    raise NotImplementedError
