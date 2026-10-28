---
title: Dựng data mart bán hàng theo Kimball trên DuckDB
level: intermediate
services: []
files:
  - path: starter/mart.sql
    note: 4 TODO
  - path: tests/test_mart.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/04-warehouse-lakehouse/exercises/intermediate/03-kimball-data-mart -q
---

## Mục tiêu

Biến các bảng staging đã làm sạch thành một data mart dạng star schema đúng chuẩn Kimball: khai báo grain,
surrogate key, unknown member, dimension ngày, và kiểm tra fact khớp số liệu với nguồn.

## Đề bài

Test tạo sẵn 4 bảng staging trong DuckDB:

| Bảng | Cột |
| --- | --- |
| `stg_customers` | `customer_id`, `customer_city`, `customer_state` |
| `stg_products` | `product_id`, `product_category_name` (có thể NULL) |
| `stg_orders` | `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp` TIMESTAMP |
| `stg_order_items` | `order_id`, `order_item_id`, `product_id`, `price`, `freight_value` |

Lưu ý dữ liệu bẩn có chủ ý: một item tham chiếu `product_id` không có trong `stg_products`.

Viết `starter/mart.sql` (nhiều câu lệnh, chạy tuần tự) tạo 4 bảng:

1. `dim_customer(customer_key INTEGER, customer_id, customer_city, customer_state)`: `customer_key` đánh số 1..n theo
   `customer_id` tăng dần, **cộng một dòng unknown member** `customer_key = 0`, `customer_id = 'unknown'`, city/state `'unknown'`.
2. `dim_product(product_key INTEGER, product_id, category)`: tương tự, `category` NULL thay bằng `'unknown'`; có dòng
   unknown member `product_key = 0`.
3. `dim_date(date_key INTEGER, full_date DATE, year, month, day, day_of_week, is_weekend BOOLEAN)`: mỗi ngày một dòng,
   **liên tục** từ ngày mua sớm nhất tới muộn nhất trong `stg_orders`. `date_key` dạng `YYYYMMDD` (vd. 20240305),
   `day_of_week` theo ISO (thứ Hai = 1 … Chủ nhật = 7), cuối tuần là 6 và 7.
4. `fact_order_items`: **grain = một dòng cho mỗi item của đơn** (`order_id`, `order_item_id`). Cột:
   `order_id`, `order_item_id`, `customer_key`, `product_key`, `date_key`, `order_status`, `price`, `freight_value`,
   `total_value` (= price + freight_value). Không tìm thấy dimension thì dùng key 0, **không được làm rơi dòng**.

Tệp phải chạy lại được trên cùng kết nối (dùng `CREATE OR REPLACE TABLE`).

## Tiêu chí đạt

- Số dòng fact bằng số dòng `stg_order_items`, khoá `(order_id, order_item_id)` không trùng.
- Mọi khoá ngoại trong fact đều có trong dimension tương ứng (không có orphan).
- Tổng `price`, `freight_value` của fact khớp staging.
- Item có sản phẩm lạ nhận `product_key = 0`.
- `dim_date` liên tục, `date_key` và `is_weekend` đúng.

## Gợi ý

### Gợi ý 1

Surrogate key: `ROW_NUMBER() OVER (ORDER BY customer_id)::INTEGER`. Unknown member: `UNION ALL SELECT 0, 'unknown', ...`.
Lịch: `SELECT unnest(generate_series(min_date, max_date, INTERVAL 1 DAY))::DATE`.

### Gợi ý 2

`date_key = CAST(strftime(d, '%Y%m%d') AS INTEGER)`, `isodow(d)` cho thứ trong tuần. Trong fact dùng `LEFT JOIN`
tới dimension và `COALESCE(dp.product_key, 0)`.
