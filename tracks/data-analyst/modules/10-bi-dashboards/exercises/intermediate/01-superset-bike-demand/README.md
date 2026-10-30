---
title: Dashboard nhu cầu xe đạp theo giờ trên Superset - dataset ảo, saved metric, chart, dashboard qua API
level: intermediate
services: [postgres, superset]
files:
  - path: starter/superset_charts.py
    note: 7 TODO - SQL dataset, 3 metric, upsert dataset/chart/dashboard, payload chart, layout
  - path: tests/test_superset_charts.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile bi up -d postgres superset
  - uv run python setup/bi/load_da.py
  - uv run python setup/bi/init_bi.py
  - uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/intermediate/01-superset-bike-demand/starter/superset_charts.py
  - uv run pytest tracks/data-analyst/modules/10-bi-dashboards/exercises/intermediate/01-superset-bike-demand -q
---

## Mục tiêu

Trưởng điều phối xe cần biết "giờ nào cần nhiều xe nhất, ngày làm việc khác cuối tuần thế nào, thời tiết xấu làm
mất bao nhiêu lượt". Bạn dựng câu trả lời trên Superset theo đúng cách một team BI làm: logic đặt ở **lớp ngữ
nghĩa** (dataset ảo có cột nhãn và saved metric dùng chung), chart chỉ chọn metric theo tên, dashboard có bố cục,
tất cả tạo bằng script idempotent. Làm xong bạn hiểu dataset/metric/chart/dashboard của Superset ở mức JSON và
vì sao metric tỉ lệ phải là biểu thức tổng hợp, không phải cột.

## Đề bài

Bảng `da.bike_hour` (17 379 giờ của Bike Sharing UCI, cột như `hour.csv`; `dteday` đang là **text**) trong
database `de` của Superset. Mở `starter/superset_charts.py`; `session` là `requests.Session` của
`setup/bi/clients.py` (đã đăng nhập, có CSRF). Các helper `dataset_name`, `rison_eq` (tham số lọc `q` của API
danh sách), `find_database_id` đã có sẵn.

1. **`DATASET_SQL`** (TODO 1): SQL của dataset ảo trên `da.bike_hour`, đúng 8 cột theo thứ tự: `day` (DATE, ép từ
   `dteday`), `hr`, `day_type` (`'Ngày làm việc'` khi `workingday = 1`, ngược lại `'Ngày nghỉ'`), `weather`
   (`weathersit` 1-4 thành `'1 · Quang, ít mây'`, `'2 · Sương mù, nhiều mây'`, `'3 · Mưa/tuyết nhẹ'`,
   `'4 · Mưa lớn, bão'`), `season`, `cnt`, `casual`, `registered`. SQL phải chạy được trên cả Postgres và DuckDB.
2. **`METRICS`** (TODO 2): ba saved metric `{"metric_name", "verbose_name", "expression"}` theo thứ tự:
   `total_rides` (tổng `cnt`), `avg_rides_per_hour` (trung bình `cnt`), `casual_share` (tổng `casual` / tổng
   `cnt`, `NULL` khi tổng `cnt` bằng 0, không chia nguyên).
3. **`upsert_dataset`** (TODO 3): tìm dataset theo `table_name`; chưa có thì `POST /api/v1/dataset/` (database,
   schema `da`, table_name, sql); có rồi thì `PUT` SQL mới rồi `PUT /api/v1/dataset/<id>/refresh` để Superset đọc
   lại cột. Sau đó đặt metric bằng `PUT /api/v1/dataset/<id>` `{"metrics": [...]}`: metric đã có cùng tên phải
   kèm `id` hiện tại (đọc từ `GET /api/v1/dataset/<id>`), nếu không Superset báo trùng.
4. **`chart_payloads`** (TODO 4): ba payload `POST /api/v1/chart/`:

   | Chart | `viz_type` | form_data (`params`) | query (`query_context.queries[0]`) |
   | --- | --- | --- | --- |
   | Lượt thuê TB mỗi giờ: ngày làm việc vs ngày nghỉ | `echarts_timeseries_line` | `x_axis: "hr"`, `groupby: ["day_type"]`, `metrics: ["avg_rides_per_hour"]` | `columns: ["hr", "day_type"]`, cùng metric |
   | Lượt thuê TB mỗi giờ theo thời tiết | `echarts_timeseries_bar` | `x_axis: "weather"`, `metrics: ["avg_rides_per_hour"]` | `columns: ["weather"]` |
   | Tỉ trọng khách vãng lai | `big_number_total` | `metric: "casual_share"`, `y_axis_format: ".1%"` | `columns: []`, `metrics: ["casual_share"]` |

   Mỗi payload: `slice_name` (bắt đầu bằng `prefix`), `viz_type`, `datasource_id`, `datasource_type: "table"`,
   `params` (chuỗi JSON, có `viz_type` và `datasource: "<id>__table"`), `query_context` (chuỗi JSON:
   `datasource {"id", "type"}`, `queries` một phần tử, `form_data`, `result_format: "json"`,
   `result_type: "full"`). `params` để giao diện vẽ chart; `query_context` để API `/api/v1/chart/<id>/data/`
   (và cache, báo cáo email) chạy lại được query.
5. **`upsert_chart`** (TODO 5): tìm theo `slice_name`, có thì `PUT`, chưa có thì `POST`.
6. **`dashboard_layout`** (TODO 6): `position_json` bản v2 như ví dụ ở phần 5 của lý thuyết; chart xếp thành các
   hàng, tối đa `per_row` chart mỗi hàng, chia đều lưới 12 cột, giữ thứ tự.
7. **`upsert_dashboard`** (TODO 7): tìm theo `dashboard_title`, chưa có thì tạo (`published: true`); `PUT`
   `position_json`; rồi gắn từng chart vào dashboard bằng `PUT /api/v1/chart/<id>` `{"dashboards": [id]}`.

Chạy script, mở link dashboard in ra. Test offline dùng DuckDB (SQL, metric) và một Superset giả trong bộ nhớ
(idempotent, không đụng chart của người khác); phần Superset thật tự skip khi chưa bật, khi chạy thì dùng tên
riêng `test-<mã> · ...` và xoá dashboard, chart, dataset đã tạo khi xong.

## Tiêu chí đạt

- SQL dataset và ba metric đúng trên dữ liệu nhỏ (gồm nhãn `weathersit = 4` và tỉ trọng `NULL` khi không có lượt).
- Payload chart dùng saved metric theo tên; layout không tràn 12 cột, mỗi chart đúng một lần.
- `publish` chạy hai lần trả cùng id; mỗi chart gắn vào dashboard.
- Trên Superset thật: dataset `virtual`, dashboard 3 chart; line có 48 điểm (24 giờ × 2 loại ngày): ngày làm
  việc 17h 525.3 và 8h 477.0 lượt/giờ, ngày nghỉ 13h 372.7; trời quang 204.87, mưa/tuyết nhẹ 111.58 lượt/giờ;
  tỉ trọng khách vãng lai 18.83%.

## Gợi ý

### Gợi ý 1

Tạo thử một chart bằng giao diện Superset, rồi gọi `GET /api/v1/chart/<id>` để xem `params` và `query_context`
thật. Postgres và DuckDB đều hiểu `CAST(dteday AS DATE)` và `CASE weathersit WHEN 1 THEN ... END`. Với tỉ trọng:
`SUM(casual) * 1.0 / NULLIF(SUM(cnt), 0)`.

### Gợi ý 2

Trong `upsert_dataset`, sau khi tạo hoặc cập nhật SQL, đọc `result.metrics` của dataset, lập `{metric_name: id}`,
rồi gửi danh sách metric của bạn với `id` cho những metric đã có. Trong `dashboard_layout`, chia
`chart_ids[i:i + per_row]`, mỗi hàng `ROW-n` có `parents: ["ROOT_ID", "GRID_ID"]`, mỗi chart
`CHART-<id>` có `parents: ["ROOT_ID", "GRID_ID", "ROW-n"]` và `meta: {"chartId", "width": 12 // per_row,
"height": 50}`.
