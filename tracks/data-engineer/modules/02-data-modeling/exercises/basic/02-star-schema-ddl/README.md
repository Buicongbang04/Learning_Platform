---
title: Viết DDL star schema cho doanh thu theo item
level: basic
services: []
files:
  - path: starter/schema.sql
    note: 6 TODO
  - path: starter/revenue_by_state_month.sql
    note: 1 TODO
  - path: tests/test_star_schema.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/02-data-modeling/exercises/basic/02-star-schema-ddl -q
---

## Mục tiêu

Biến một thiết kế star schema thành DDL chạy được: surrogate key, khoá ngoại, `dim_date` sinh
bằng SQL, và một truy vấn phân tích trên star schema.

## Đề bài

Grain của fact: **một dòng = một item trong một đơn hàng**.

1. Trong `starter/schema.sql` (DuckDB), tạo:
   - `dim_date(date_key INTEGER PK, full_date DATE, year INTEGER, quarter INTEGER, month INTEGER, day INTEGER, day_of_week INTEGER, is_weekend BOOLEAN)`.
     `date_key` dạng `YYYYMMDD` (ví dụ `20180131`). `day_of_week` theo ISO: thứ Hai = 1, Chủ nhật = 7.
     `is_weekend` đúng với thứ Bảy, Chủ nhật.
   - Đổ `dim_date` đủ mọi ngày từ `2017-01-01` tới `2018-12-31` (730 dòng).
   - `dim_customer(customer_key INTEGER PK, customer_id VARCHAR NOT NULL, city VARCHAR, state VARCHAR)`
   - `dim_product(product_key INTEGER PK, product_id VARCHAR NOT NULL, category_name VARCHAR)`
   - `dim_seller(seller_key INTEGER PK, seller_id VARCHAR NOT NULL, city VARCHAR, state VARCHAR)`
   - `fact_order_items(order_id VARCHAR, order_item_id INTEGER, purchase_date_key, customer_key, product_key, seller_key, price DECIMAL(10,2), freight_value DECIMAL(10,2))`
     với khoá chính `(order_id, order_item_id)` và 4 khoá ngoại tới 4 dimension.
2. Trong `starter/revenue_by_state_month.sql`, viết truy vấn trả về `year, month, state, revenue`
   (tổng `price`, theo bang của khách), sắp theo `year, month, revenue DESC`.

## Tiêu chí đạt

- 5 bảng có đủ cột như đề; khoá chính và khoá ngoại được khai báo.
- `dim_date` có đúng 730 dòng, `date_key`, `quarter`, `day_of_week`, `is_weekend` đúng.
- Chèn fact tham chiếu `customer_key` không tồn tại bị database từ chối.
- Truy vấn doanh thu trả đúng kết quả trên dữ liệu mẫu của test.

## Gợi ý

### Gợi ý 1

DuckDB có `generate_series(DATE '2017-01-01', DATE '2018-12-31', INTERVAL 1 DAY)` (trả về
TIMESTAMP, ép `::DATE`), và các hàm `year()`, `quarter()`, `month()`, `day()`, `isodow()`.

### Gợi ý 2

`date_key = year(d) * 10000 + month(d) * 100 + day(d)`. Khoá ngoại:
`purchase_date_key INTEGER REFERENCES dim_date (date_key)`.
