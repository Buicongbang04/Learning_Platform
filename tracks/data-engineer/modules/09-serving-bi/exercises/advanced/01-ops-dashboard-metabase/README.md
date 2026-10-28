---
title: Dashboard vận hành giao hàng trên Metabase, dashboard as code
level: advanced
services: [metabase]
files:
  - path: starter/marts.sql
    note: 3 TODO, serving marts
  - path: starter/dashboard.py
    note: 2 TODO, spec dashboard và publish qua API
  - path: tests/test_ops_dashboard.py
    note: Không sửa
  - path: tests/fixtures/olist_small.sql
    note: Dữ liệu Olist thu nhỏ, không sửa
run:
  - uv run pytest tracks/data-engineer/modules/09-serving-bi/exercises/advanced/01-ops-dashboard-metabase -q
  - docker compose -f setup/docker-compose.yml up -d metabase
  - METABASE_USER=you@example.com METABASE_PASSWORD=... METABASE_DB_ID=2 uv run pytest tracks/data-engineer/modules/09-serving-bi/exercises/advanced/01-ops-dashboard-metabase -q
---

## Mục tiêu

Làm trọn một dashboard vận hành từ dưới lên: thiết kế các bảng serving đúng grain cho từng câu hỏi của đội vận hành,
thiết kế bố cục dashboard theo nguyên tắc KPI → xu hướng → hành động, và quản lý dashboard như code (publish lên
Metabase qua API, chạy lại không tạo trùng). Bài này là bước chuẩn bị cho milestone m09 của capstone.

## Đề bài

Đội logistics của Olist cần một màn hình mở mỗi sáng để trả lời: hôm nay bao nhiêu đơn, tỉ lệ giao trễ có vượt 5%
không, đơn nào đang quá hạn chưa giao và của seller nào, seller nào hay trễ.

1. **`starter/marts.sql`**: dựng 3 bảng (giữ tên và cột, có thể thêm mart khác):
   - `mart_ops_daily`: theo ngày đặt, chỉ đơn hợp lệ: `orders`, `delivered_orders`, `late_orders`, `late_rate`
     (NULL khi không có đơn delivered), `revenue`, `updated_at`.
   - `mart_overdue_orders`: đơn chưa giao, không huỷ, đã quá ngày dự kiến tính tới `run_context.as_of`: thêm
     `days_overdue` và `seller_ids` (nối bằng dấu phẩy, tăng dần).
   - `mart_seller_late_rate`: theo seller, trên các đơn delivered có item của seller.
2. **`starter/dashboard.py`**:
   - `dashboard_spec()`: ít nhất 4 card. Hàng đầu có tối thiểu 2 KPI tile (`scalar`); có biểu đồ `line` cho xu hướng;
     có bảng `table` đọc `mart_overdue_orders` để hành động. Card chỉ đọc bảng `mart_*`, không chồng nhau, nằm trong
     lưới 24 cột.
   - `publish(spec, base_url, username, password, database_id)`: đăng nhập, tạo/cập nhật card native query, tạo hoặc
     cập nhật dashboard theo tên, gắn card đúng vị trí. Chạy hai lần trả cùng id dashboard.
3. **Chạy với Metabase thật** (tuỳ chọn nhưng nên làm): nạp các mart vào Postgres của `setup/` (hoặc database Metabase
   đọc được), bật Metabase, tạo admin lần đầu, đặt biến môi trường như lệnh `run` và chạy test publish. Chụp màn hình
   dashboard, đặt thêm alert khi late rate vượt 5%.

## Tiêu chí đạt

- 4 test dữ liệu và spec pass không cần Docker; test publish pass khi bật Metabase (hoặc skip khi chưa bật).
- Mỗi mart có grain rõ ràng, không fan-out, xử lý đúng trường hợp không có đơn delivered.
- Dashboard đọc như một câu chuyện: KPI có ngữ cảnh (target, so sánh), xu hướng, rồi danh sách việc cần làm.
- `publish` idempotent, không lộ mật khẩu trong code (đọc từ biến môi trường).
- Có ghi chú ngắn (trong docstring hoặc README riêng của bạn) về lịch refresh mart và cách hiển thị freshness.

## Gợi ý

### Gợi ý 1

Tính tiền mỗi đơn trong một CTE riêng trước khi join với đơn, để `COUNT` đơn không bị fan-out. Với seller, đưa về
cặp `(seller_id, order_id)` duy nhất bằng `SELECT DISTINCT` rồi mới đếm. `date_diff('day', a, b)` và
`string_agg(DISTINCT seller_id, ',' ORDER BY seller_id)` có sẵn trong DuckDB.

### Gợi ý 2

Metabase API: `POST /api/session` trả `id` dùng làm header `X-Metabase-Session`. Card native query:
`{"name", "display", "visualization_settings": {}, "dataset_query": {"type": "native", "database": db_id,
"native": {"query": sql}}}`. Tìm dashboard cũ bằng `GET /api/dashboard` theo tên; gắn card bằng
`PUT /api/dashboard/:id` với danh sách `dashcards` (`id` âm cho card mới, kèm `card_id`, `row`, `col`, `size_x`,
`size_y`). Kiểm tra đúng tên field theo phiên bản Metabase bạn chạy ở `/api/docs`.
