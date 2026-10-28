---
title: CTE đệ quy, date spine và gaps-and-islands
level: intermediate
services: []
files:
  - path: starter/category_tree.sql
    note: 1 TODO
  - path: starter/category_rollup.sql
    note: 1 TODO
  - path: starter/daily_sales_filled.sql
    note: 1 TODO
  - path: starter/customer_streaks.sql
    note: 1 TODO
  - path: tests/test_recursive.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/01-foundations/exercises/intermediate/01-sql-recursive-gaps -q
---

## Mục tiêu

Giải ba dạng bài SQL mà Data Engineer gặp liên tục: duyệt dữ liệu phân cấp bằng `WITH RECURSIVE`,
lấp ngày trống bằng date spine, và tìm chuỗi liên tiếp (gaps-and-islands) bằng window function.

## Đề bài

Test tạo sẵn trong DuckDB:

- `categories(category_id INTEGER, parent_id INTEGER, name VARCHAR)`: cây danh mục, gốc có
  `parent_id IS NULL`, độ sâu không giới hạn.
- `products(product_id, category_id)`, `order_items(order_id, product_id, price DECIMAL(10,2))`.
- `daily_sales(sale_date DATE, amount DECIMAL(10,2))`: giao dịch thô, một ngày có thể nhiều dòng
  hoặc không có dòng nào.
- `orders(order_id, customer_id, order_purchase_timestamp TIMESTAMP)`.

Mỗi tệp là **một** câu `SELECT`:

1. **`category_tree.sql`**: mọi danh mục với `category_id, name, depth, path`. Gốc có `depth = 0`;
   `path` là tên các tổ tiên nối bằng `' > '`, ví dụ `Casa > Moveis > Moveis Sala`. Sắp theo `path`.
   Phải dùng `WITH RECURSIVE`.
2. **`category_rollup.sql`**: mỗi danh mục với `category_id, name, own_revenue, total_revenue`.
   `own_revenue` là tổng `price` của sản phẩm gắn trực tiếp vào danh mục; `total_revenue` gồm cả mọi
   danh mục con cháu. Danh mục không có doanh thu ghi `0` (không phải `NULL`). Sắp theo
   `category_id`. Phải dùng `WITH RECURSIVE`.
3. **`daily_sales_filled.sql`**: mỗi ngày từ ngày nhỏ nhất tới ngày lớn nhất trong `daily_sales`
   (kể cả ngày không có giao dịch), cột `sale_date, amount` với `amount = 0` cho ngày trống. Sắp
   theo `sale_date`.
4. **`customer_streaks.sql`**: với mỗi khách, `customer_id, longest_streak` là số **tháng lịch liên
   tiếp** dài nhất mà khách có ít nhất một đơn (tháng 12/2017 và 1/2018 là liên tiếp). Sắp theo
   `customer_id`.

## Tiêu chí đạt

- Bốn truy vấn trả đúng cột và giá trị trên dữ liệu test.
- `category_tree` và `category_rollup` dùng CTE đệ quy, đúng với cây sâu tuỳ ý.
- Date spine không bỏ sót ngày, ngày trống là `0`.
- Streak tính đúng qua ranh giới năm và khi một tháng có nhiều đơn.

## Gợi ý

### Gợi ý 1

Cho `category_rollup`, dựng bảng "tổ tiên – con cháu" (closure) bằng đệ quy: anchor là mỗi danh mục
với chính nó `(ancestor_id = category_id, descendant_id = category_id)`, bước đệ quy nối thêm con
của `descendant_id`. Sau đó `total_revenue` = tổng `own_revenue` của mọi descendant.

### Gợi ý 2

Date spine: `WITH RECURSIVE days(d) AS (SELECT MIN(sale_date) ... UNION ALL SELECT d + 1 ... WHERE d < (SELECT MAX(...)))`
(DuckDB còn có `generate_series`). Streak: đổi tháng thành số nguyên
`year(m) * 12 + month(m)`, trừ `ROW_NUMBER()` theo khách; các tháng liên tiếp có cùng hiệu, đếm
theo nhóm đó rồi lấy `MAX`. Nhớ `DISTINCT` tháng trước khi đánh số.
