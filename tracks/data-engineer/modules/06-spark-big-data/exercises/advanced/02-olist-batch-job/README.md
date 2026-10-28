---
title: Job batch Olist - CSV thô tới Parquet partition, chạy lại idempotent
level: advanced
services: []
files:
  - path: starter/pipeline.py
    note: 4 TODO
  - path: tests/test_pipeline.py
    note: Không sửa
  - path: tests/fixtures/orders.csv
    note: Dữ liệu mẫu có lỗi cố ý
  - path: tests/fixtures/order_items.csv
    note: Dữ liệu mẫu có lỗi cố ý
run:
  - uv run pytest tracks/data-engineer/modules/06-spark-big-data/exercises/advanced/02-olist-batch-job -q
---

## Mục tiêu

Viết một job Spark batch hoàn chỉnh như ở production: đọc CSV với schema khai báo, làm sạch, tổng
hợp, ghi Parquet partition theo `year`/`month`, và **chạy lại được** (cả toàn bộ lẫn backfill một tháng)
mà không nhân đôi dữ liệu hay xoá nhầm tháng khác.

## Đề bài

Sửa `starter/pipeline.py` (schema `ORDERS_SCHEMA`, `ITEMS_SCHEMA` đã có sẵn):

1. `read_raw(spark, orders_csv, items_csv)`: đọc hai tệp CSV có header bằng schema khai báo (không
   `inferSchema`), trả về tuple `(orders, items)`.
2. `clean(orders, items)`: trả về `(orders, items)` đã làm sạch:
   - `orders`: bỏ dòng thiếu `order_id` hoặc `order_purchase_timestamp`; chuẩn hoá `order_status`
     (`trim` + `lower`); bỏ trùng theo `order_id`.
   - `items`: bỏ dòng `price` null hoặc âm; bỏ trùng theo `(order_id, order_item_id)`.
3. `daily_seller_gmv(orders, items)`: chỉ đơn `delivered`; mỗi `(order_date, seller_id)` một dòng với
   `n_orders` (số đơn khác nhau, kiểu long), `gmv` (tổng `price`, làm tròn 2), và hai cột partition
   `year`, `month` (int) lấy từ `order_date`. Thứ tự cột:
   `order_date, seller_id, n_orders, gmv, year, month`.
4. `run(spark, orders_csv, items_csv, out_path, year=None, month=None)`: chạy cả pipeline và ghi Parquet
   vào `out_path`, `partitionBy("year", "month")`.
   - Không truyền `year`/`month`: xử lý toàn bộ dữ liệu.
   - Có `year`, `month`: chỉ xử lý và ghi đè **đúng tháng đó**, các tháng khác trong `out_path` giữ nguyên.
   - Chạy lại bao nhiêu lần với cùng đầu vào cũng cho cùng kết quả (idempotent).

Viết thêm trong docstring đầu tệp: vì sao bạn chọn cách ghi đè này, và cách làm tương đương với Delta
Lake (`replaceWhere` hoặc `MERGE`).

## Tiêu chí đạt

- Tất cả test pass, gồm test chạy lại hai lần và test backfill một tháng.
- Không dùng `collect()`/`toPandas()` trong pipeline (trừ khi để log).
- Mỗi thư mục partition chỉ có ít file (không ghi 200 file nhỏ cho mỗi tháng).
- Cấu hình SparkSession bạn thay đổi được khôi phục sau `run` (khuyến khích, không bắt buộc).

## Gợi ý

### Gợi ý 1

`spark.read.option("header", True).option("timestampFormat", "yyyy-MM-dd HH:mm:ss").schema(...).csv(path)`.
Ô rỗng trong CSV được đọc thành `null`.

### Gợi ý 2

`spark.sql.sources.partitionOverwriteMode = dynamic` + `mode("overwrite")`: Spark chỉ thay các partition
xuất hiện trong DataFrame đang ghi. Lọc tháng **trước** khi aggregate để backfill rẻ.
