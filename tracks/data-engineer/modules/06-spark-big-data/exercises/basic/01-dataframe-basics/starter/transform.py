"""DataFrame cơ bản trên dữ liệu Olist."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F  # noqa: F401


def delivered_orders(orders: DataFrame) -> DataFrame:
    # TODO: lọc order_status == "delivered" (lower + trim)
    raise NotImplementedError


def add_purchase_month(orders: DataFrame) -> DataFrame:
    # TODO: thêm cột purchase_month dạng "yyyy-MM" từ order_purchase_timestamp
    raise NotImplementedError


def revenue_by_state(orders: DataFrame, customers: DataFrame, payments: DataFrame) -> DataFrame:
    # TODO: delivered -> join customers, payments -> groupBy customer_state
    #       cột: customer_state, n_orders, revenue; sắp xếp revenue giảm dần, state tăng dần
    raise NotImplementedError
