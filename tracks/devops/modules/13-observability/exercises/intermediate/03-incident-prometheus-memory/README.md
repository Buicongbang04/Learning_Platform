---
title: Sự cố - Prometheus phình RAM sau lần đổi cấu hình Collector
level: intermediate
services: []
files:
  - path: starter/observability/otel-collector/config.yaml
    note: Cấu hình Collector đang chạy production
  - path: tests/test_incident.py
    note: Không sửa
  - path: tests/fixtures/incident/config.yaml
    note: Bản gốc cho ca hồi quy, không sửa
run:
  - uv run pytest tracks/devops/modules/13-observability/exercises/intermediate/03-incident-prometheus-memory -q -rs
---

## Mục tiêu

Chẩn đoán một sự cố của chính hệ thống observability từ triệu chứng, bằng truy vấn trên Prometheus, rồi sửa tối thiểu sao cho dashboard
vẫn giữ được góc nhìn mà team cần.

## Đề bài

Thứ Hai tuần trước, team Olist Shop deploy bản cấu hình Collector mới (`starter/observability/otel-collector/config.yaml`) để dashboard
spanmetrics "chi tiết hơn". Từ đó:

- RAM của Prometheus tăng đều mỗi ngày, cuối tuần chạm giới hạn container và bị OOM kill hai lần. Mỗi lần khởi động lại, replay WAL mất
  gần 10 phút, trong thời gian đó không có alert nào được đánh giá.
- `prometheus_tsdb_head_series` tăng theo đường gần như song song với tổng số request của API, cả ngày lẫn đêm, không có dấu hiệu bão hoà.
  Trước lần deploy, con số này đứng yên ở vài nghìn.
- Panel spanmetrics trên dashboard mở mất hơn 30 giây; query `sum by (span_name) (rate(traces_span_metrics_calls_total[5m]))` bị
  timeout giờ cao điểm.
- Log Collector không có lỗi. Trace vẫn tới Jaeger bình thường. Rollback image của API về bản tuần trước không đỡ.
- Team vẫn cần trên dashboard: số lời gọi và thời gian theo từng span (route), tách theo method và mã HTTP.

Sửa `starter/observability/otel-collector/config.yaml`. Không đổi code app, không đổi Prometheus.

**Cách test chấm.** Test dựng Olist Shop cùng `ObsStack` với cấu hình của bạn, gửi 40 request `GET /orders/...` tới các đơn hàng khác
nhau, rồi kiểm:

- Tổng lời gọi của span `GET /orders/{order_id}` với `http_response_status_code="404"` trong spanmetrics đủ 40.
- Số series `traces_span_metrics_calls_total{service_name="olist-shop-api"}` không quá 20, tức không lớn lên theo số request.
- Trace kèm span DB vẫn tới Jaeger.

Một ca hồi quy chạy cùng kịch bản với bản gốc (`tests/fixtures/incident/config.yaml`) và chứng minh nó tái hiện triệu chứng. Mỗi ca dựng
stack riêng, khoảng 40 giây và RAM khoảng 650 MB; lần đầu build image cần mạng.

Muốn tự điều tra như trên production: đặt breakpoint trong test sau khi gửi request (hay chạy stack bằng tay theo
`setup/DEVOPS-TOOLS.md`), mở Prometheus ở `stack.url("prometheus")`, trang `Status → TSDB Status`.

## Tiêu chí đạt

- Mọi test pass, kể cả ca hồi quy.
- Viết được 3 dòng "nguyên nhân, cách sửa, cách phát hiện sớm lần sau" mà không cần đọc lời giải.
- Nói được một cách giữ lại thông tin chi tiết hơn mà không làm Prometheus phình.

## Gợi ý

### Gợi ý 1

Đừng đọc cấu hình trước. Hỏi Prometheus: metric nào có nhiều series nhất (`topk(10, count by (__name__) ({__name__=~".+"}))`), rồi trong
metric đó, nhãn nào có nhiều giá trị khác nhau nhất (`count(count by (<nhãn>) (<metric>))` cho từng nhãn). Trang `TSDB Status` cũng liệt kê
sẵn.

### Gợi ý 2

So số giá trị khác nhau của mỗi nhãn với số request đã gửi. Nhãn nào tỉ lệ thuận với traffic thì không thuộc về metric, kể cả khi nó hữu
ích: thông tin đó đã có ở nơi khác rẻ hơn.
