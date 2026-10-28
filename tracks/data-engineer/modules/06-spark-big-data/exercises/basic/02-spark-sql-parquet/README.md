---
title: Spark SQL và Parquet partition theo năm/tháng
level: basic
services: []
files:
  - path: starter/sql_parquet.py
    note: 4 TODO
  - path: tests/test_sql_parquet.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/06-spark-big-data/exercises/basic/02-spark-sql-parquet -q
---

## Mục tiêu

Viết truy vấn Spark SQL trên temp view, ghi Parquet partition theo `year`/`month` và đọc lại chỉ một
partition (partition pruning).

## Đề bài

Sửa `starter/sql_parquet.py`:

1. `register_views(orders, items)`: đăng ký hai temp view tên `orders` và `order_items`.
2. `monthly_gmv(spark)`: chạy **một câu `spark.sql`** trên hai view trên, chỉ đơn `delivered`, trả về
   cột `month` (chuỗi `yyyy-MM` từ `order_purchase_timestamp`), `n_orders` (số đơn khác nhau),
   `gmv` (tổng `price + freight_value`, làm tròn 2), sắp xếp theo `month` tăng dần.
3. `write_partitioned(orders, path)`: thêm cột `year`, `month` (số nguyên, từ
   `order_purchase_timestamp`), ghi Parquet vào `path` với `partitionBy("year", "month")`, mode
   `overwrite`. Thư mục kết quả có dạng `path/year=2018/month=1/part-*.parquet`.
4. `read_month(spark, path, year, month)`: đọc lại Parquet ở `path` và chỉ lấy một tháng. Spark phải chỉ
   quét đúng thư mục của tháng đó.

Schema:

- `orders(order_id, customer_id, order_status, order_purchase_timestamp)` (timestamp là chuỗi)
- `order_items(order_id, order_item_id int, product_id, seller_id, price double, freight_value double)`

## Tiêu chí đạt

- `monthly_gmv` dùng `spark.sql`, không dùng DataFrame API cho phần tính toán.
- Sau `write_partitioned` có thư mục `year=2018/month=1`.
- Physical plan của `read_month(...)` có `PartitionFilters` khác rỗng (partition pruning), và mọi dòng đọc được đều đến từ thư mục của tháng được hỏi.
- Tất cả test pass.

## Gợi ý

### Gợi ý 1

`df.createOrReplaceTempView("orders")`. Trong SQL: `date_format(to_timestamp(o.order_purchase_timestamp), 'yyyy-MM')`.

### Gợi ý 2

Lọc bằng cột partition (`filter((F.col("year") == year) & (F.col("month") == month))`) ngay sau
`spark.read.parquet(path)`; xem `explain()` thấy `PartitionFilters`.
