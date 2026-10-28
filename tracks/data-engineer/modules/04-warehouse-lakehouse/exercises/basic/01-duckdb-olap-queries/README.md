---
title: Truy vấn OLAP với DuckDB (ROLLUP, window function)
level: basic
services: []
files:
  - path: starter/revenue_rollup.sql
    note: 1 TODO
  - path: starter/top_products.sql
    note: 1 TODO
  - path: starter/monthly_running.sql
    note: 1 TODO
  - path: tests/test_olap_queries.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/04-warehouse-lakehouse/exercises/basic/01-duckdb-olap-queries -q
---

## Mục tiêu

Viết được ba kiểu truy vấn phân tích hay gặp nhất trên warehouse: tổng hợp nhiều cấp (subtotal, grand total)
bằng `GROUP BY ROLLUP`, top-N theo nhóm bằng window function, và luỹ kế / tăng trưởng theo tháng bằng `SUM() OVER` và `LAG`.

## Đề bài

Test tạo sẵn trong DuckDB (in-memory) ba bảng nhỏ kiểu Olist:

| Bảng | Cột |
| --- | --- |
| `orders` | `order_id`, `customer_state`, `order_status`, `order_purchase_timestamp` (TIMESTAMP) |
| `order_items` | `order_id`, `order_item_id`, `product_id`, `price` (DOUBLE) |
| `products` | `product_id`, `product_category_name` |

Doanh thu (`revenue`) = tổng `price` của các item thuộc đơn có `order_status = 'delivered'`. Tháng (`order_month`)
là chuỗi `'YYYY-MM'` lấy từ `order_purchase_timestamp`. Chỉ tính đơn `delivered` ở cả ba câu.

1. `starter/revenue_rollup.sql`: doanh thu theo `customer_state` và `order_month`, có dòng subtotal cho từng
   bang (`order_month` là NULL) và một dòng grand total (cả hai cột NULL). Cột trả về: `customer_state`,
   `order_month`, `revenue`. Sắp xếp `customer_state NULLS LAST, order_month NULLS LAST`.
2. `starter/top_products.sql`: với mỗi `product_category_name`, lấy 2 sản phẩm có doanh thu cao nhất.
   Cột: `category`, `product_id`, `revenue`, `rnk` (1 hoặc 2). Hoà doanh thu thì `product_id` nhỏ hơn đứng trước
   (dùng `ROW_NUMBER`). Sắp xếp `category, rnk`.
3. `starter/monthly_running.sql`: doanh thu theo tháng, kèm `cumulative_revenue` (luỹ kế từ tháng đầu) và
   `mom_growth_pct` = (revenue − revenue tháng trước) / revenue tháng trước × 100, làm tròn 2 chữ số, tháng đầu là NULL.
   Cột: `order_month`, `revenue`, `cumulative_revenue`, `mom_growth_pct`. Sắp xếp theo `order_month`.

Mỗi tệp chứa đúng một câu `SELECT` (có thể dùng `WITH`). Không tạo bảng.

## Tiêu chí đạt

- `revenue_rollup.sql` trả đúng các dòng chi tiết, subtotal theo bang và grand total.
- `top_products.sql` trả tối đa 2 sản phẩm mỗi category, đúng thứ tự và xử lý hoà đúng.
- `monthly_running.sql` tính đúng luỹ kế và tăng trưởng MoM, tháng đầu `mom_growth_pct` là NULL.
- `uv run pytest ... -q` pass.

## Gợi ý

### Gợi ý 1

`strftime(order_purchase_timestamp, '%Y-%m')` cho ra tháng. `GROUP BY ROLLUP (a, b)` sinh các nhóm `(a, b)`, `(a)`, `()`.
Window function chạy *sau* `GROUP BY`, nên có thể viết `SUM(SUM(price)) OVER (ORDER BY ...)`.

### Gợi ý 2

Top-N: tính doanh thu theo `(category, product_id)` trong một CTE, rồi
`ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC, product_id)` và lọc bằng `QUALIFY rnk <= 2`
(DuckDB hỗ trợ `QUALIFY`). MoM: `LAG(revenue) OVER (ORDER BY order_month)`.
