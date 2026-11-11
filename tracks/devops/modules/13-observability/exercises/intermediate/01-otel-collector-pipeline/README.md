---
title: Pipeline OTel Collector cho Olist Shop - OTLP vào, Jaeger và Prometheus ra
level: intermediate
services: []
files:
  - path: starter/observability/otel-collector/config.yaml
    note: 3 TODO
  - path: tests/test_collector.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/13-observability/exercises/intermediate/01-otel-collector-pipeline -q -rs
---

## Mục tiêu

Tự viết cấu hình OpenTelemetry Collector: nhận OTLP từ API và worker, gắn attribute môi trường, gửi trace sang Jaeger, sinh metric từ span
(spanmetrics) cho Prometheus, và giữ log chảy tới Loki. Hiểu receiver, processor, exporter, connector ghép thành pipeline thế nào.

## Đề bài

Olist Shop gửi trace và log bằng OTLP gRPC tới `otel-collector:4317` (biến `OTEL_EXPORTER_OTLP_ENDPOINT`). Span có: HTTP `SERVER`
(`GET /orders/{order_id}`), query Postgres `CLIENT` (thuộc tính `db.system.name=postgresql`), `send olist:jobs` `PRODUCER` ở API và
`process olist:jobs` `CONSUMER` ở worker. `starter/observability/otel-collector/config.yaml` thay cấu hình Collector mặc định của stack;
bản starter chỉ in trace ra log (`debug`) và gửi log tới Loki.

Hoàn thiện cấu hình:

1. **Processor `resource`** (đặt tên tuỳ ý, ví dụ `resource/env`) gắn `deployment.environment.name=lab` cho mọi span. Danh sách
   processor của pipeline traces bắt đầu bằng `memory_limiter`, kết thúc bằng `batch`.
2. **Trace sang Jaeger**: exporter `otlp` (ví dụ `otlp/jaeger`) tới `jaeger:4317`, không TLS trong mạng lab.
3. **Spanmetrics sang Prometheus**: connector `spanmetrics` là exporter của pipeline traces và receiver của pipeline metrics; thêm
   dimension `http.response.status_code`; `metrics_flush_interval` tối đa `15s` (mặc định 60 giây là quá lâu cho test); histogram có
   bucket explicit. Pipeline metrics xuất bằng exporter `prometheus` ở `0.0.0.0:8889` (Prometheus của stack scrape `otel-collector:8889`).
4. Giữ pipeline logs gửi tới `otlphttp/loki`.

**Cách test chấm.** Hai test tĩnh đọc YAML (thứ tự processor, attribute, exporter, connector, dimension). Test thật dựng Olist Shop
cùng `ObsStack` với Collector của bạn, gửi 3 request `GET /orders/...` (404) và một job, rồi kiểm:

| Kiểm | Ở đâu |
| --- | --- |
| Trace `GET /orders/{order_id}` có span DB postgresql là con của span HTTP | Jaeger |
| Trace của job đi qua cả `olist-shop-api` và `olist-shop-worker` | Jaeger |
| Resource attribute `deployment.environment.name=lab` trên span của cả hai service | Jaeger (API v3) |
| `traces_span_metrics_calls_total{..., http_response_status_code="404"}` có giá trị | Prometheus |
| `histogram_quantile(0.95, ...)` trên histogram thời gian của span DB ra số | Prometheus |
| Log của request vẫn tới Loki, khớp `trace_id` | Loki |

Lần đầu build image Olist Shop cần mạng; stack khoảng 35 giây, RAM khoảng 650 MB. Collector không khởi động được (YAML sai, tên
component sai) thì test fail kèm log của nó.

Kiểm cú pháp trước khi chạy test, trong thư mục `starter/observability/otel-collector/`:

```bash
docker run --rm --network none -v "$PWD:/conf:ro" \
  otel/opentelemetry-collector-contrib:0.163.2@sha256:7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849 \
  validate --config=/conf/config.yaml
```

## Tiêu chí đạt

- Mọi test pass.
- Giải thích được vì sao `memory_limiter` đứng đầu và `batch` đứng cuối.
- Nói được connector khác exporter ở đâu, và vì sao spanmetrics là connector.
- Biết đổi exporter Jaeger sang một backend khác (Tempo, vendor SaaS) mà không sửa code app.

## Gợi ý

### Gợi ý 1

Một component khai ở mục cấp trên (`processors:`, `exporters:`, `connectors:`) chỉ chạy khi được nhắc tên trong `service.pipelines`.
Connector xuất hiện hai lần: trong `exporters` của pipeline traces và trong `receivers` của pipeline metrics. Tên dạng `kiểu/tên` (`otlp/jaeger`).

### Gợi ý 2

```yaml
processors:
  resource/env:
    attributes:
      - {key: deployment.environment.name, value: lab, action: upsert}
connectors:
  spanmetrics:
    metrics_flush_interval: 5s
    dimensions: [{name: http.response.status_code}]
    histogram: {explicit: {buckets: [5ms, 25ms, 100ms, 500ms, 1s]}}
```

Exporter `otlp` tới Jaeger cần `tls: {insecure: true}`.
