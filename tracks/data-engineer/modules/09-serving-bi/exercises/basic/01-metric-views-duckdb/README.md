---
title: Định nghĩa metric bằng SQL view trên DuckDB
level: basic
services: []
files:
  - path: starter/metrics.sql
    note: 4 TODO
  - path: tests/test_metrics.py
    note: Không sửa
  - path: tests/fixtures/olist_small.sql
    note: Dữ liệu Olist thu nhỏ, không sửa
run:
  - uv run pytest tracks/data-engineer/modules/09-serving-bi/exercises/basic/01-metric-views-duckdb -q
---

## Mục tiêu

Dựng một metric layer tối giản bằng view: một fact table sạch làm nền, các view metric dựng trên nó, để mọi
dashboard dùng chung một định nghĩa doanh thu, AOV và tỉ lệ giao trễ. Bạn sẽ gặp hai bẫy hay gặp: tính ratio
sai grain và fan-out khi join.

## Đề bài

Test nạp `tests/fixtures/olist_small.sql` (bảng `customers`, `orders`, `order_items`) vào DuckDB in-memory rồi
chạy `starter/metrics.sql`. Viết lại thân 4 view (giữ nguyên tên view và tên cột):

1. `fct_order_items`: grain một dòng `order_items`, gồm `order_id`, `order_date` (kiểu DATE, từ
   `order_purchase_timestamp`), `customer_state`, `order_status`, `product_id`, `price`, `freight_value`.
   Bỏ đơn `canceled` và `unavailable`.
2. `metric_daily_revenue`: theo `order_date`: `orders` (số đơn khác nhau), `revenue` (tổng `price`),
   `aov = ROUND(revenue / orders, 2)`.
3. `metric_state_summary`: theo `customer_state`: `orders`, `revenue`, `aov` như trên, và
   `revenue_share = ROUND(revenue / tổng revenue của mọi state, 4)`.
4. `metric_late_rate_by_state`: chỉ đơn `delivered`, theo `customer_state`: `delivered_orders`, `late_orders`
   (đơn có `order_delivered_customer_date > order_estimated_delivery_date`),
   `late_rate = ROUND(late_orders / delivered_orders, 4)`.

View 2 và 3 phải dựng trên `fct_order_items`, không lặp lại logic lọc trạng thái.

## Tiêu chí đạt

- `fct_order_items` có 7 dòng, không có đơn `o4` (canceled).
- `metric_daily_revenue` ra đúng 3 ngày với `orders`, `revenue`, `aov` khớp test.
- `metric_state_summary` có `revenue_share` cộng lại bằng 1.
- `metric_late_rate_by_state` đếm đơn RJ là 2, không phải 3 (không fan-out).
- Tổng `revenue` và `orders` của các view khớp với `fct_order_items`.
- `uv run pytest … -q` pass 5 test.

## Gợi ý

### Gợi ý 1

`CAST(order_purchase_timestamp AS DATE)` cho ngày. AOV là `SUM(price) / COUNT(DISTINCT order_id)` ở đúng grain
của view, đừng lấy trung bình các AOV nhỏ hơn. Với share, dùng window function `SUM(revenue) OVER ()` trên kết quả
đã group.

### Gợi ý 2

`metric_late_rate_by_state` chỉ cần `orders` join `customers`. Nếu join thêm `order_items`, đơn có 2 item bị đếm 2
lần. Trong DuckDB, `COUNT(*) FILTER (WHERE is_late)` gọn hơn `SUM(CASE WHEN … THEN 1 ELSE 0 END)`. Lưu ý phép chia
số nguyên trong DuckDB `/` trả DOUBLE, còn `//` mới là chia nguyên.
