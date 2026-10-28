"""DataFrame cơ bản trên dữ liệu Olist (lời giải)."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def delivered_orders(orders: DataFrame) -> DataFrame:
    return orders.filter(F.lower(F.trim(F.col("order_status"))) == "delivered")


def add_purchase_month(orders: DataFrame) -> DataFrame:
    return orders.withColumn(
        "purchase_month",
        F.date_format(F.to_timestamp("order_purchase_timestamp"), "yyyy-MM"),
    )


def revenue_by_state(orders: DataFrame, customers: DataFrame, payments: DataFrame) -> DataFrame:
    return (
        delivered_orders(orders)
        .select("order_id", "customer_id")
        .join(customers.select("customer_id", "customer_state"), "customer_id")
        .join(payments.select("order_id", "payment_value"), "order_id")
        .groupBy("customer_state")
        .agg(
            F.countDistinct("order_id").alias("n_orders"),
            F.round(F.sum("payment_value"), 2).alias("revenue"),
        )
        .orderBy(F.desc("revenue"), F.asc("customer_state"))
    )
