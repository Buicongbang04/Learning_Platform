# Hướng giải: Job batch Olist idempotent

Không có một đáp án duy nhất. Dưới đây là hướng làm, quyết định thiết kế và rubric.

## Phác thảo

```python
def read_raw(spark, orders_csv, items_csv):
    reader = spark.read.option("header", True).option("timestampFormat", "yyyy-MM-dd HH:mm:ss")
    return reader.schema(ORDERS_SCHEMA).csv(orders_csv), reader.schema(ITEMS_SCHEMA).csv(items_csv)


def clean(orders, items):
    orders = (
        orders.dropna(subset=["order_id", "order_purchase_timestamp"])
        .withColumn("order_status", F.lower(F.trim("order_status")))
        .dropDuplicates(["order_id"])
    )
    items = items.filter(F.col("price").isNotNull() & (F.col("price") >= 0)) \
                 .dropDuplicates(["order_id", "order_item_id"])
    return orders, items


def daily_seller_gmv(orders, items):
    delivered = (
        orders.filter(F.col("order_status") == "delivered")
        .select("order_id", F.to_date("order_purchase_timestamp").alias("order_date"))
    )
    return (
        items.select("order_id", "seller_id", "price")
        .join(delivered, "order_id")
        .groupBy("order_date", "seller_id")
        .agg(F.countDistinct("order_id").alias("n_orders"), F.round(F.sum("price"), 2).alias("gmv"))
        .withColumn("year", F.year("order_date"))
        .withColumn("month", F.month("order_date"))
        .select("order_date", "seller_id", "n_orders", "gmv", "year", "month")
    )


def run(spark, orders_csv, items_csv, out_path, year=None, month=None):
    orders, items = clean(*read_raw(spark, orders_csv, items_csv))
    if year is not None and month is not None:
        ts = F.col("order_purchase_timestamp")
        orders = orders.filter((F.year(ts) == year) & (F.month(ts) == month))
    result = daily_seller_gmv(orders, items)

    key = "spark.sql.sources.partitionOverwriteMode"
    old = spark.conf.get(key)
    spark.conf.set(key, "dynamic")
    try:
        (result.repartition("year", "month")
            .write.mode("overwrite").partitionBy("year", "month").parquet(out_path))
    finally:
        spark.conf.set(key, old)
```

## Quyết định thiết kế cần cân nhắc

- **Schema khai báo** thay vì `inferSchema`: không quét dữ liệu hai lần, kiểu ổn định giữa các lần
  chạy, dữ liệu sai kiểu thành `null` (mode `PERMISSIVE`) để bước clean xử lý. Có thể dùng
  `mode=FAILFAST` hoặc `columnNameOfCorruptRecord` để ghi lại dòng lỗi vào bảng quarantine.
- **Dedup tất định**: `dropDuplicates(["order_id"])` giữ dòng bất kỳ. Nếu các bản trùng khác nhau (CDC),
  dùng `row_number` theo `updated_at` như bài intermediate 03.
- **Ghi đè theo partition**: `partitionOverwriteMode=dynamic` chỉ thay thư mục partition có trong
  DataFrame. Với `static` (mặc định), `mode("overwrite")` xoá cả `out_path` → backfill tháng 2 làm mất
  tháng 1. `mode("append")` thì chạy lại sẽ nhân đôi. Khôi phục cấu hình trong `finally`.
- **Lọc trước khi aggregate**: backfill tháng 2 chỉ đọc/tính tháng 2. Ở đây lọc theo `orders` là đủ vì
  join loại item của tháng khác. Nếu nguồn đã partition theo ngày, lọc ngay ở `read` để có partition pruning.
- **Small files**: `repartition("year", "month")` trước khi ghi cho mỗi tháng một file (dữ liệu lớn thì
  thêm `spark.sql.files.maxRecordsPerFile` hoặc repartition theo số file mong muốn).
- **Đơn delivered của tháng trước cập nhật muộn**: trong thực tế, chạy lại cửa sổ vài ngày/tháng gần nhất
  (late-arriving data) thay vì chỉ đúng một tháng.
- **Delta Lake**: tương đương là
  `df.write.format("delta").mode("overwrite").option("replaceWhere", "year = 2018 AND month = 2")`, hoặc
  `MERGE INTO target USING source ON (order_date, seller_id)`. Delta cho ghi atomic (không có trạng thái
  nửa vời nếu job chết giữa chừng), điều Parquet thuần trên object storage không bảo đảm.
- **Tính atomic**: với Parquet thuần, nếu job chết lúc đang ghi, partition có thể trống hoặc thiếu file.
  Cách giảm rủi ro: ghi ra thư mục tạm rồi đổi tên, hoặc dùng table format (Delta/Iceberg).

## Rubric (100 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Test đọc với schema và clean pass | 15 |
| `daily_seller_gmv` đúng (countDistinct, làm tròn, kiểu cột) | 20 |
| `run` toàn bộ idempotent, ít file mỗi partition | 20 |
| Backfill một tháng giữ nguyên tháng khác, chạy lại vẫn đúng | 20 |
| Khôi phục cấu hình SparkSession sau khi dùng | 5 |
| Docstring giải thích lựa chọn ghi đè và phương án Delta Lake | 10 |
| Code rõ ràng, không collect/toPandas, lọc sớm | 10 |

Trừ điểm: `mode("append")`, xoá thư mục bằng `shutil.rmtree` thay vì dùng cơ chế của Spark (không chạy
được trên S3/HDFS), `inferSchema`.
