---
title: Dashboard Grafana as code cho service ETA
level: intermediate
services: [grafana, prometheus]
files:
  - path: starter/dashboard.json
    note: JSON dashboard, điền tiêu đề, biến và 6 panel
  - path: starter/provider.yml
    note: File provider để Grafana nạp dashboard từ đĩa
  - path: tests/test_dashboard.py
    note: Không sửa
run:
  - docker compose -f setup/mlops/compose.yaml --profile monitoring up -d --wait
  - uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/intermediate/01-grafana-dashboard-as-code -q
---

## Mục tiêu

Dashboard sửa bằng chuột trong UI là dashboard không ai review, không ai khôi phục khi Grafana mất volume. Bài này viết dashboard
thành tệp JSON và provider YAML để đưa vào Git, rồi kiểm bằng chính Grafana: nó nhận dashboard và mọi câu truy vấn đều là PromQL hợp lệ.

## Đề bài

Cần stack `monitoring` đang chạy (lệnh trong `run` ở trên; test skip kèm lệnh bật khi Grafana chưa lên). Grafana ở
`127.0.0.1:23000` (đổi qua `MLOPS_GRAFANA_PORT`), đăng nhập `admin`/`admin`, đã có datasource tên `Prometheus`. Bạn **không** sửa
`setup/mlops`; test đẩy dashboard của bạn qua API với `uid` và tiêu đề riêng rồi xoá đi, nên chạy lại bao nhiêu lần cũng không để rác.

Hoàn thiện `starter/dashboard.json`:

- `title` không rỗng; `tags` chứa `mlops` và `eta`; `schemaVersion` từ 39; `refresh` là `30s` hoặc `1m`; thời gian mặc định
  `time.from` là `now-6h`; không có trường `id` số (để `uid` cố định, test sẽ thay bằng uid riêng, nhưng `uid` của bạn dài tối đa 40 ký tự).
- Datasource là **biến**: `templating.list` có biến `datasource` kiểu `datasource` với `query` là `prometheus`. Mọi panel và mọi
  target dùng đúng `{"type": "prometheus", "uid": "${datasource}"}`, không ghi cứng uid của máy bạn.
- Ít nhất 6 panel, `id` khác nhau, `type` thuộc `timeseries`, `stat`, `table`, `gauge`, `bargauge`, `histogram`, `barchart`, `heatmap`; `gridPos` nằm trong
  lưới 24 cột (`w` và `h` từ 3) và không panel nào chồng lên panel khác.
- Phải có (kiểm theo biểu thức, không theo tiêu đề): request rate (`http_requests_total` qua `rate(`); tỉ lệ lỗi 5xx của `/predict`
  (một phép chia, lọc `status=~"5.."`); độ trễ p95 là `histogram_quantile(0.95, ... sum by (le) (rate(http_request_duration_seconds_bucket ...)))`;
  phiên bản model từ `eta_model_info` dạng `stat` hoặc `table`; phân phối dự đoán từ `eta_prediction_seconds_bucket` qua
  `histogram_quantile`; tỉ lệ fallback từ `rate(eta_fallback_total ...)`.
- Counter (tên chứa `_total`) không bao giờ vẽ thô: luôn qua `rate(` hoặc `increase(`.
- Trong biểu thức chỉ dùng macro `$__rate_interval`; không dùng biến dashboard nào khác.

Hoàn thiện `starter/provider.yml` (file provider của Grafana): `apiVersion: 1`, đúng một provider `type: file`, `folder` không
rỗng, `disableDeletion: true`, `allowUiUpdates: false`, `updateIntervalSeconds` từ 10, `options.path` bắt đầu bằng
`/var/lib/grafana/dashboards`.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/intermediate/01-grafana-dashboard-as-code -q` pass.
- Test gửi từng biểu thức qua `/api/ds/query` và Grafana không báo lỗi parse; sau test dashboard không còn trong Grafana.
- Bạn giải thích được vì sao `allowUiUpdates: false` và `disableDeletion: true` hợp với dashboard as code, và vì sao biến `datasource` tốt hơn uid cứng.

## Gợi ý

### Gợi ý 1

Cách nhanh nhất để có JSON chuẩn: dựng panel trong Grafana UI, mở "Export", bật "Export for sharing externally", rồi dọn tay:
bỏ `id`, thay uid datasource bằng `${datasource}`. Đừng commit nguyên bản export.

### Gợi ý 2

Panel `stat` cho `eta_model_info` hiển thị nhãn `version` bằng `legendFormat: "{{version}}"`. `$__rate_interval` luôn tối thiểu
4 lần khoảng scrape nên tốt hơn ghi cứng `[5m]` hay `[1m]` trong dashboard.
