---
title: Dashboard RED của Olist Shop provision từ Git vào Grafana
level: basic
services: []
files:
  - path: starter/observability/grafana/provisioning/dashboards/dashboards.yaml
    note: Provider dashboard, thay tệp mặc định của stack
  - path: starter/observability/grafana/dashboards/olist-api.json
    note: Dashboard JSON
  - path: tests/test_dashboard.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/13-observability/exercises/basic/02-grafana-dashboard-provisioning -q -rs
---

## Mục tiêu

Viết dashboard thành tệp trong Git và để Grafana tự nạp lúc khởi động (provisioning), thay vì kéo thả trên UI. Dashboard đi theo RED
(Rate, Errors, Duration) cho API, thêm thông lượng worker và một panel log, và mọi query phải trả dữ liệu thật.

## Đề bài

Thư mục `starter/observability/` có cùng cấu trúc với `setup/observability/` của stack: tệp nào bạn đặt ở đây thì thay tệp mặc định
cùng đường dẫn. Grafana của stack mount `grafana/provisioning/` vào `/etc/grafana/provisioning` và `grafana/dashboards/` vào
`/etc/grafana/dashboards`, và đã có datasource provision sẵn với `uid` cố định: `prometheus`, `loki`, `jaeger`.

**1. Provider** `grafana/provisioning/dashboards/dashboards.yaml`: một provider `type: file`, `folder: Olist Shop`, `options.path:
/etc/grafana/dashboards`, `allowUiUpdates: false`, `disableDeletion: true`, `updateIntervalSeconds` từ 10 tới 300.

**2. Dashboard** `grafana/dashboards/olist-api.json`:

- `uid: olist-api-red`, `title` của bạn, `tags` có `olist` và `red`, `schemaVersion` từ 39.
- Ít nhất 5 panel, `type` thuộc `timeseries`, `stat`, `gauge`, `bargauge`, `table`, `logs`, `heatmap`; `gridPos` có `x`, `y`, `w`, `h`
  trong lưới 24 cột.
- Datasource của mọi panel và query ghi bằng `{"type": "prometheus", "uid": "prometheus"}` hay `{"type": "loki", "uid": "loki"}`,
  không dùng placeholder kiểu `${DS_PROMETHEUS}` của JSON export (placeholder đó chỉ được thay khi import bằng tay trên UI).
- Phải có, kiểm theo biểu thức chứ không theo tiêu đề:

| Panel | Metric |
| --- | --- |
| Rate | `rate(http_requests_total{job="olist-api"} ...)` theo `path` |
| Errors | Tỉ lệ request 5xx trên tổng request (một phép chia, lọc nhãn mã HTTP theo `5..`) |
| Duration | `histogram_quantile(0.95, ...)` trên `http_request_duration_seconds_bucket`, giữ `le` |
| Worker | `rate(jobs_processed_total{job="olist-worker"} ...)` |
| Log | Panel `type: logs`, query Loki trên `{service_name="olist-shop-api"}` chỉ lấy dòng request lỗi 5xx |

- Counter (tên đuôi `_total`) luôn đi qua `rate()` hay `increase()`; cửa sổ trong dashboard là `[$__rate_interval]`, không ghi cứng `[5m]`.

Log của API trong Loki là dòng JSON như `{"msg": "request", "request_id": "...", "trace_id": "...", "path": "/readyz", "status": 503,
...}`, nhãn stream `service_name`.

**Cách test chấm.** Các test tĩnh đọc hai tệp. Test cuối dựng Olist Shop cùng `ObsStack` với thư mục `observability/` của bạn, kiểm
Grafana đã nạp dashboard vào đúng folder, gửi traffic (request thường, hai job, rồi dừng Redis để `/readyz` trả 503), rồi chạy **từng
query** của dashboard qua chính Grafana (`/api/ds/query`, khoảng 15 phút gần nhất) và đòi mỗi query trả dữ liệu. Lần đầu build image
Olist Shop cần mạng; stack khoảng 50 giây, RAM khoảng 650 MB.

Muốn xem dashboard bằng mắt: chạy stack bằng tay theo `setup/DEVOPS-TOOLS.md` mục "Stack observability" sau khi chép hai tệp vào
`setup/observability/` của một bản chép (đừng sửa bản gốc), hoặc đặt breakpoint trong test và mở `stack.url("grafana")`.

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được `$__rate_interval` khác `[5m]` thế nào khi zoom từ 15 phút ra 7 ngày.
- Nói được vì sao `allowUiUpdates: false` và dashboard trong Git là cùng một quyết định: nguồn sự thật nằm ở đâu.

## Gợi ý

### Gợi ý 1

Cách nhanh nhất để có JSON đúng hình: dựng stack, vẽ panel trên UI (đăng nhập không cần, nhưng Viewer không lưu được; tạm đặt
`GF_AUTH_ANONYMOUS_ORG_ROLE: Editor` trong bản chép compose của bạn), rồi "Export → Export as JSON" và **sửa lại** datasource thành
uid cố định. Hoặc viết tay: mỗi panel cần `id`, `type`, `title`, `datasource`, `gridPos`, `targets` (`refId`, `expr`).

### Gợi ý 2

Query log lỗi: `{service_name="olist-shop-api"} | json | status >= 500`. Tỉ lệ lỗi:
`sum(rate(...{..., status=~"5.."}[$__rate_interval])) / sum(rate(...[$__rate_interval]))`.
