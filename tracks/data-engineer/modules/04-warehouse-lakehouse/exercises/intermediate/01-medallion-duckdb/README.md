---
title: Pipeline medallion bronze → silver → gold bằng DuckDB
level: intermediate
services: []
files:
  - path: starter/medallion.py
    note: 3 TODO
  - path: tests/test_medallion.py
    note: Không sửa
  - path: tests/fixtures/orders_raw.csv
    note: Dữ liệu thô có lỗi cố ý
run:
  - uv run pytest tracks/data-engineer/modules/04-warehouse-lakehouse/exercises/intermediate/01-medallion-duckdb -q
---

## Mục tiêu

Tự dựng kiến trúc medallion trên tệp Parquet: bronze giữ nguyên dữ liệu thô kèm metadata nạp, silver làm sạch,
ép kiểu và khử trùng lặp, gold tổng hợp sẵn cho BI. Hiểu mỗi tầng chịu trách nhiệm gì và vì sao không gộp làm một.

## Đề bài

`tests/fixtures/orders_raw.csv` là bản export đơn hàng có lỗi cố ý: dòng trùng hệt nhau, cùng `order_id` nhưng
nhiều phiên bản (`updated_at` khác nhau), trạng thái viết hoa/thừa khoảng trắng, timestamp hỏng, `order_id` rỗng,
`order_value` không phải số. Hoàn thiện 3 hàm trong `starter/medallion.py`, mỗi hàm nhận một kết nối DuckDB:

1. `load_bronze(con, csv_path, bronze_dir) -> int`: đọc CSV **toàn bộ cột là VARCHAR** (không để DuckDB đoán kiểu),
   thêm `_source_file` (tên tệp, không kèm thư mục) và `_ingested_at` (thời điểm nạp), ghi `bronze_dir/orders.parquet`.
   Trả số dòng. Bronze không bỏ dòng nào.
2. `build_silver(con, bronze_dir, silver_dir) -> int`: đọc bronze, ghi `silver_dir/orders.parquet` với các cột
   `order_id` VARCHAR, `customer_id` VARCHAR, `order_status` VARCHAR (đã `trim` + `lower`),
   `order_purchase_timestamp` TIMESTAMP, `order_value` DOUBLE, `updated_at` TIMESTAMP. Quy tắc:
   - bỏ dòng có `order_id` rỗng/NULL hoặc `order_purchase_timestamp` không ép kiểu được;
   - `order_value` không ép được thì để NULL (giữ dòng);
   - mỗi `order_id` chỉ giữ một dòng: bản có `updated_at` mới nhất.
   Trả số dòng silver.
3. `build_gold(con, silver_dir, gold_dir) -> int`: ghi `gold_dir/daily_revenue.parquet` gồm `order_date` DATE,
   `delivered_orders` BIGINT, `revenue` DOUBLE (tổng `order_value`, bỏ qua NULL) chỉ cho đơn `delivered`,
   sắp theo ngày. Trả số dòng.

Chạy lại bất kỳ hàm nào cũng phải cho cùng kết quả (ghi đè tệp, không nối thêm).

## Tiêu chí đạt

- Bronze có đủ 12 dòng, mọi cột dữ liệu là VARCHAR, có `_source_file = 'orders_raw.csv'` và `_ingested_at`.
- Silver có đúng 7 đơn, đúng kiểu, trạng thái đã chuẩn hoá, `o002` là `delivered`, `o008` là `canceled`.
- Gold khớp doanh thu theo ngày của đơn delivered.
- Chạy hai lần liên tiếp không đổi kết quả.

## Gợi ý

### Gợi ý 1

`read_csv(path, all_varchar = true)`. Ghi bằng `COPY (SELECT ...) TO 'file.parquet' (FORMAT parquet)`;
`COPY` ghi đè tệp đơn sẵn có. `TRY_CAST(x AS TIMESTAMP)` trả NULL thay vì lỗi.

### Gợi ý 2

Khử trùng lặp theo bản mới nhất:

```sql
SELECT * FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY updated_at DESC) = 1
```
