---
title: Partition dữ liệu theo năm/tháng kiểu Hive với DuckDB
level: basic
services: []
files:
  - path: starter/partitioning.py
    note: 4 TODO
  - path: tests/test_partitioning.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/04-warehouse-lakehouse/exercises/basic/03-hive-partitioning -q
---

## Mục tiêu

Biết cách bố trí dữ liệu trên data lake theo partition kiểu Hive (`year=2024/month=3/…`), đọc lại có
partition pruning, và hiểu cột partition được "mã hoá" trong đường dẫn chứ không nằm trong tệp.

## Đề bài

Test tạo trong DuckDB bảng `orders(order_id, customer_state, order_status, order_purchase_timestamp, payment_value)`
khoảng 400 dòng trải từ 2023-11 tới 2024-04. Hoàn thiện `starter/partitioning.py`:

1. `write_partitioned(con, table, out_dir)`: ghi bảng `table` ra `out_dir` dạng Parquet, partition theo
   `year` và `month` (số nguyên, tính từ `order_purchase_timestamp`) bằng `COPY ... (FORMAT parquet, PARTITION_BY (year, month))`.
   Nếu `out_dir` đã có dữ liệu thì ghi đè (chạy lại không bị nhân đôi).
2. `list_partitions(out_dir)`: trả list `(year, month)` dạng `int`, sắp tăng dần, đọc từ tên thư mục.
3. `monthly_revenue(con, out_dir, year, month)`: tổng `payment_value` của đơn `delivered` trong tháng đó,
   đọc bằng `read_parquet(..., hive_partitioning = true)` có điều kiện trên `year`, `month`.
4. `revenue_by_month(con, out_dir)`: list `(year, month, revenue)` cho mọi tháng (đơn `delivered`), sắp tăng dần.

## Tiêu chí đạt

- Thư mục ra có dạng `out_dir/year=YYYY/month=M/*.parquet`, đủ 6 partition.
- Tệp Parquet bên trong **không** chứa cột `year`, `month` (chúng nằm ở đường dẫn).
- Gọi `write_partitioned` hai lần vẫn cho cùng tổng số dòng.
- `monthly_revenue` và `revenue_by_month` khớp kết quả tính trên bảng gốc.

## Gợi ý

### Gợi ý 1

```sql
COPY (SELECT *, year(order_purchase_timestamp) AS year, month(order_purchase_timestamp) AS month FROM orders)
TO 'out_dir' (FORMAT parquet, PARTITION_BY (year, month), OVERWRITE_OR_IGNORE)
```

Ghi đè sạch sẽ nhất là xoá thư mục cũ (`shutil.rmtree`) trước khi `COPY`.

### Gợi ý 2

Đọc: `read_parquet('out_dir/**/*.parquet', hive_partitioning = true)`. Dùng tham số `?` khi truyền `year`, `month`.
Tên thư mục `year=2024` tách bằng `name.split("=")`.
