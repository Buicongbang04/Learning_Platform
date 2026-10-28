"""Báo cáo seller Olist: phiên bản chậm cần tối ưu.

TODO: viết lại toàn bộ tệp này cho nhanh, giữ nguyên chữ ký và kết quả.
TODO: liệt kê ở đây các anti-pattern bạn đã sửa và vì sao mỗi cái chậm.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

REPORT_SCHEMA = "seller_id string, seller_state string, n_orders long, gmv double"


def seller_report(
    spark: SparkSession, orders: DataFrame, items: DataFrame, sellers: DataFrame
) -> DataFrame:
    def tier(gmv):
        if gmv >= 1000:
            return "gold"
        if gmv >= 200:
            return "silver"
        return "bronze"

    tier_udf = F.udf(tier, StringType())

    delivered = orders.filter(F.col("order_status") == "delivered")

    # Vòng lặp Python: mỗi seller vài Spark job
    seller_ids = [r.seller_id for r in items.select("seller_id").distinct().collect()]
    rows = []
    for sid in seller_ids:
        sub = items.filter(F.col("seller_id") == sid).join(delivered, "order_id")
        n_orders = sub.select("order_id").distinct().count()
        if n_orders == 0:
            continue
        gmv = sub.agg(F.sum("price")).first()[0]
        state = sellers.filter(F.col("seller_id") == sid).first().seller_state
        rows.append((sid, state, n_orders, round(gmv, 2)))

    report = spark.createDataFrame(rows, REPORT_SCHEMA)
    report = report.withColumn("avg_ticket", F.round(F.col("gmv") / F.col("n_orders"), 2))
    report = report.withColumn("tier", tier_udf(F.col("gmv")))
    return report.orderBy(F.desc("gmv"), F.asc("seller_id"))


def tier_counts(report: DataFrame) -> dict:
    result = {}
    for t in ["gold", "silver", "bronze"]:
        n = report.filter(F.col("tier") == t).count()  # mỗi tier một job, tính lại cả report
        if n:
            result[t] = n
    return result
