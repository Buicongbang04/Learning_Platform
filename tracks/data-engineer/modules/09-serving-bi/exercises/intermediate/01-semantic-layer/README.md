---
title: Tự viết semantic layer sinh SQL cho DuckDB
level: intermediate
services: []
files:
  - path: starter/semantic.py
    note: 3 TODO (registry metric đã có sẵn)
  - path: tests/test_semantic.py
    note: Không sửa
  - path: tests/fixtures/olist_small.sql
    note: Dữ liệu Olist thu nhỏ, không sửa
run:
  - uv run pytest tracks/data-engineer/modules/09-serving-bi/exercises/intermediate/01-semantic-layer -q
---

## Mục tiêu

Hiểu semantic layer (dbt MetricFlow, Cube, LookML) hoạt động thế nào bằng cách tự viết một bản nhỏ: nhận yêu cầu
"metric X theo dimension Y, lọc Z", sinh SQL đúng grain, không fan-out, tính ratio sau khi aggregate, và chặn SQL
injection.

## Đề bài

`starter/semantic.py` đã có registry:

- `MODELS`: hai bảng logic ở hai grain, `items` (một dòng order_items) và `orders` (một dòng đơn hàng).
- `DIMENSIONS`: `order_date`, `order_month`, `customer_state`, `order_status`, dùng được cho mọi model.
- `MEASURES`: phép aggregate gắn với một model (`revenue` trên `items`, `orders` trên `orders`, …).
- `METRICS`: metric `simple` (trỏ tới một measure) hoặc `ratio` (numerator / denominator).

Viết ba hàm:

1. `validate_request(metrics, dimensions=(), filters=())`: raise `ValueError` cho metric/dimension không có trong
   registry, metrics rỗng, op filter không thuộc `FILTER_OPS`, hoặc `in` với giá trị không phải list/tuple khác rỗng.
2. `compile_query(metrics, dimensions=(), filters=())` trả `(sql, params)`:
   - Gom các measure cần thiết theo model; mỗi model một CTE aggregate ở grain các dimension được yêu cầu.
   - Nối các CTE bằng `FULL OUTER JOIN … USING (dims)` (không có dimension thì `CROSS JOIN`).
   - Ratio tính ở SELECT cuối: `numerator / NULLIF(denominator, 0)`.
   - Cột kết quả: dimension theo thứ tự yêu cầu, rồi metric theo thứ tự yêu cầu. `ORDER BY` các dimension.
   - Giá trị filter đi vào `params` qua `?`.
3. `run_query(con, …)`: chạy và trả `list[dict]`.

Ví dụ: `run_query(con, ["aov", "late_rate"], ["customer_state"], [("order_status", "in", ["delivered"])])`.

## Tiêu chí đạt

- `aov` toàn bộ = 146.0 (730 / 5), `late_rate` = 0.75.
- Lấy `items` và `orders` theo state cùng lúc vẫn ra 4/3 cho SP và 3/2 cho RJ (không fan-out).
- Filter `=`, `in`, `<=` hoạt động; nhiều dimension cùng lúc hoạt động.
- Giá trị filter chứa `'` không xuất hiện trong SQL và không trả về dữ liệu.
- Tên dimension/metric lạ bị từ chối bằng `ValueError`.
- `uv run pytest … -q` pass 14 test.

## Gợi ý

### Gợi ý 1

Bắt đầu từ trường hợp một model: `SELECT <dims>, <aggs> FROM (<model sql>) AS base WHERE … GROUP BY 1, 2`. Khi chạy
được rồi mới thêm model thứ hai thành CTE thứ hai. Mỗi CTE có cùng mệnh đề `WHERE`, nên `params` của filter phải
được thêm một lần cho mỗi CTE, đúng thứ tự xuất hiện của dấu `?`.

### Gợi ý 2

Với ratio, các CTE trả về measure thô (`revenue`, `orders`), SELECT cuối viết `revenue / NULLIF(orders, 0) AS aov`.
Trong DuckDB, cột trong `USING` được gộp lại, nên SELECT cuối gọi thẳng `customer_state` không cần tiền tố bảng.
Tên dimension và metric chỉ được lấy từ key của registry, đó là lý do whitelist chặn được injection.
