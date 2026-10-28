---
title: DataFrame cơ bản - doanh thu Olist theo bang
level: basic
services: []
files:
  - path: starter/transform.py
    note: 3 TODO
  - path: tests/test_transform.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/06-spark-big-data/exercises/basic/01-dataframe-basics -q
---

## Mục tiêu

Làm quen DataFrame API của PySpark: `filter`, `withColumn`, `join`, `groupBy().agg()`, và thấy chúng
giống/khác pandas ở đâu (lazy, chạy phân tán).

## Đề bài

Trong `starter/transform.py` có ba hàm, mỗi hàm nhận và trả về `pyspark.sql.DataFrame`:

1. `delivered_orders(orders)`: giữ các đơn có `order_status == "delivered"` (không phân biệt hoa thường,
   bỏ khoảng trắng hai đầu). Giữ nguyên các cột.
2. `add_purchase_month(orders)`: thêm cột `purchase_month` dạng chuỗi `yyyy-MM` lấy từ cột
   `order_purchase_timestamp` (chuỗi `yyyy-MM-dd HH:mm:ss`).
3. `revenue_by_state(orders, customers, payments)`: chỉ tính đơn delivered; join `orders` với
   `customers` (theo `customer_id`) và `payments` (theo `order_id`, một đơn có thể nhiều dòng payment).
   Trả về đúng ba cột `customer_state`, `n_orders` (số đơn khác nhau), `revenue` (tổng
   `payment_value`, làm tròn 2 chữ số), sắp xếp `revenue` giảm dần rồi `customer_state` tăng dần.

Schema đầu vào:

- `orders(order_id, customer_id, order_status, order_purchase_timestamp)`
- `customers(customer_id, customer_state)`
- `payments(order_id, payment_type, payment_value double)`

## Tiêu chí đạt

- Không dùng `toPandas()`/`collect()` bên trong hàm: hàm chỉ dựng plan.
- `delivered_orders` nhận cả `" Delivered "`.
- `revenue_by_state` không đếm trùng đơn có nhiều payment trong `n_orders`.
- Tất cả test trong `tests/test_transform.py` pass.

## Gợi ý

### Gợi ý 1

`F.lower(F.trim(F.col("order_status")))`, `F.substring(col, 1, 7)` hoặc
`F.date_format(F.to_timestamp(col), "yyyy-MM")`.

### Gợi ý 2

`.agg(F.countDistinct("order_id").alias("n_orders"), F.round(F.sum("payment_value"), 2).alias("revenue"))`
rồi `.orderBy(F.desc("revenue"), "customer_state")`.
