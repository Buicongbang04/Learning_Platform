"""Job batch Olist: CSV thô -> làm sạch -> GMV theo ngày và seller -> Parquet partition.

TODO: giải thích cách ghi đè idempotent bạn chọn và cách tương đương với Delta Lake.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F  # noqa: F401

ORDERS_SCHEMA = (
    "order_id string, customer_id string, order_status string, order_purchase_timestamp timestamp"
)
ITEMS_SCHEMA = (
    "order_id string, order_item_id int, product_id string, seller_id string, "
    "price double, freight_value double"
)


def read_raw(spark: SparkSession, orders_csv: str, items_csv: str) -> tuple[DataFrame, DataFrame]:
    # TODO: đọc CSV có header với schema khai báo
    raise NotImplementedError


def clean(orders: DataFrame, items: DataFrame) -> tuple[DataFrame, DataFrame]:
    # TODO: làm sạch theo đề bài
    raise NotImplementedError


def daily_seller_gmv(orders: DataFrame, items: DataFrame) -> DataFrame:
    # TODO: delivered -> join -> groupBy(order_date, seller_id) -> thêm year, month
    raise NotImplementedError


def run(
    spark: SparkSession,
    orders_csv: str,
    items_csv: str,
    out_path: str,
    year: int | None = None,
    month: int | None = None,
) -> None:
    # TODO: chạy pipeline, ghi Parquet partitionBy(year, month), idempotent, backfill một tháng
    raise NotImplementedError
