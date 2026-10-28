---
title: Chuẩn hoá bảng đơn hàng phẳng về 3NF
level: basic
services: []
files:
  - path: starter/normalize.sql
    note: 5 TODO
  - path: tests/test_normalize.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/02-data-modeling/exercises/basic/01-normalize-orders -q
---

## Mục tiêu

Tách một bảng export phẳng kiểu Olist thành các bảng 3NF có khoá chính, khoá ngoại, và chứng minh
không mất thông tin khi join lại.

## Đề bài

Test tạo sẵn trong DuckDB bảng `orders_flat`, mỗi dòng là một item của một đơn hàng:

| Cột | Ý nghĩa |
| --- | --- |
| `order_id`, `order_item_id` | Khoá của dòng (đơn hàng + số thứ tự item) |
| `customer_id`, `customer_city`, `customer_state` | Thông tin khách (phụ thuộc `customer_id`) |
| `order_status`, `order_purchase_timestamp` | Thông tin đơn (phụ thuộc `order_id`) |
| `product_id`, `product_category_name` | Sản phẩm (danh mục phụ thuộc `product_id`) |
| `seller_id`, `seller_city`, `seller_state` | Người bán (phụ thuộc `seller_id`) |
| `price`, `freight_value` | Giá và phí vận chuyển của item |

Viết `starter/normalize.sql` tạo 5 bảng và đổ dữ liệu từ `orders_flat`:

- `customers(customer_id PK, customer_city, customer_state)`
- `sellers(seller_id PK, seller_city, seller_state)`
- `products(product_id PK, product_category_name)`
- `orders(order_id PK, customer_id FK → customers, order_status, order_purchase_timestamp)`
- `order_items(order_id FK → orders, order_item_id, product_id FK → products, seller_id FK → sellers, price, freight_value)`, khoá chính `(order_id, order_item_id)`

Tên cột giữ nguyên như bảng phẳng. Mỗi bảng chỉ chứa đúng các cột liệt kê ở trên.

## Tiêu chí đạt

- Đủ 5 bảng, đúng tập cột, không cột thừa (ví dụ `orders` không còn `customer_city`).
- Mỗi bảng có `PRIMARY KEY` như mô tả; `orders` và `order_items` có `FOREIGN KEY`.
- Số dòng: mỗi thực thể xuất hiện đúng một lần.
- Join 5 bảng lại cho ra đúng `orders_flat` (không thừa, không thiếu dòng).

## Gợi ý

### Gợi ý 1

Tạo bảng cha trước (customers, sellers, products), rồi `orders`, cuối cùng `order_items`, vì khoá
ngoại cần bảng được tham chiếu tồn tại.

### Gợi ý 2

`CREATE TABLE customers (customer_id VARCHAR PRIMARY KEY, ...);` rồi
`INSERT INTO customers SELECT DISTINCT customer_id, customer_city, customer_state FROM orders_flat;`.
`CREATE TABLE AS SELECT` không tạo được khoá chính, nên tách thành hai câu.
