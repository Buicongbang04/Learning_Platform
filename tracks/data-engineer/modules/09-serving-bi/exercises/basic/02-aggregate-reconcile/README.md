---
title: Bảng aggregate theo ngày và kiểm tra số khớp nguồn
level: basic
services: []
files:
  - path: starter/aggregate.py
    note: 2 TODO
  - path: tests/test_aggregate.py
    note: Không sửa
  - path: tests/fixtures/olist_small.sql
    note: Dữ liệu Olist thu nhỏ, không sửa
run:
  - uv run pytest tracks/data-engineer/modules/09-serving-bi/exercises/basic/02-aggregate-reconcile -q
---

## Mục tiêu

Pre-compute một bảng serving cho dashboard (`agg_daily_sales`) theo cách idempotent, rồi viết kiểm tra
reconcile để chắc chắn số trong bảng aggregate khớp bảng nguồn, chỉ ra được ngày nào lệch.

## Đề bài

Hoàn thiện `starter/aggregate.py`:

1. `build_agg_daily_sales(con, start, end)`:
   - Tạo bảng `agg_daily_sales` nếu chưa có (đã có sẵn `DDL`).
   - Grain `(order_date, customer_state)`, `order_date` là ngày của `order_purchase_timestamp`.
   - Cột: `orders` (số đơn khác nhau), `items` (số dòng `order_items`), `revenue` (`SUM(price)`),
     `freight` (`SUM(freight_value)`). Chỉ tính đơn thoả `VALID_STATUS_FILTER`.
   - Chỉ tính lại các ngày trong `[start, end]` (cả hai đầu). Chạy lại nhiều lần không nhân đôi dữ liệu, ngày ngoài
     khoảng giữ nguyên. Truyền ngày bằng tham số `?`.
   - Trả số dòng của bảng trong khoảng sau khi build.
2. `reconcile(con, start, end, tolerance=0.01)` trả dict `ok`, `agg_revenue`, `src_revenue`, `agg_orders`,
   `src_orders`, `mismatched_dates`. Một ngày bị coi là lệch khi số đơn khác nhau hoặc revenue chênh lớn hơn
   `tolerance`, kể cả khi ngày đó chỉ có ở một phía (ví dụ đơn đến muộn chưa được aggregate).

## Tiêu chí đạt

- Build cả tháng 8/2018 ra đúng 4 dòng như test.
- Build từng phần và build lặp lại vẫn ra cùng kết quả.
- `reconcile` trả `ok=True` khi khớp; phát hiện đúng ngày bị sửa tay; bỏ qua chênh lệch nhỏ hơn `tolerance`.
- Khi có đơn mới đến muộn, `reconcile` báo đúng ngày lệch; build lại ngày đó thì hết lệch.
- `uv run pytest … -q` pass 6 test.

## Gợi ý

### Gợi ý 1

Mẫu idempotent đơn giản nhất: `DELETE … WHERE order_date BETWEEN ? AND ?` rồi `INSERT INTO agg_daily_sales SELECT …`
với cùng điều kiện. Bọc hai lệnh trong `BEGIN TRANSACTION` / `COMMIT` để người đọc không thấy bảng trống giữa chừng.
DuckDB nhận chuỗi ngày qua `CAST(? AS DATE)`.

### Gợi ý 2

Với reconcile, aggregate hai phía về grain ngày trong hai CTE, rồi `FULL OUTER JOIN` theo `order_date` và
`COALESCE(…, 0)` để bắt được ngày chỉ có ở một phía. So sánh số thực bằng `abs(a - b) > tolerance`, không dùng `!=`.
