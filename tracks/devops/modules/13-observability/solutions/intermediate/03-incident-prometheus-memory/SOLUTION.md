# Lời giải: Prometheus phình vì spanmetrics có dimension `url.path`

## Nguyên nhân

Bản cấu hình mới thêm dimension `url.path` cho connector `spanmetrics`. Span HTTP của Olist Shop có cả `http.route` (template
`/orders/{order_id}`, tên span cũng dùng nó) lẫn `url.path` (đường dẫn thật, `/orders/e481f51cbdc54678b7cc49136f2d6af7`). Mỗi đơn hàng
khác nhau là một giá trị nhãn mới, tức một bộ series mới: `calls_total` cộng một series cho mỗi bucket của histogram thời gian (11 bucket
cộng `_sum`, `_count`). 40 request trong test thành hơn 40 series `calls_total`; production với hàng trăm nghìn đơn mỗi ngày thành hàng
triệu series. Series trong head block nằm trong RAM, nên RAM tăng theo traffic, và WAL dài ra làm khởi động lại chậm.

Không có lỗi ở đâu vì không có gì "sai" về cú pháp: Collector làm đúng việc được bảo, Prometheus nhận mọi series. Rollback app không đỡ vì
nguyên nhân nằm ở Collector.

## Cách sửa

Bỏ `url.path` khỏi `dimensions` (xem `config.yaml`). `span_name` đã là `METHOD route`, nên team vẫn có số lời gọi và thời gian theo route,
tách theo method và mã HTTP. Các cách khác cũng qua test:

- Đổi dimension thành `http.route` (bounded, nhưng trùng thông tin với `span_name`).
- Dùng processor `transform` để chuẩn hoá `url.path` thành template trước spanmetrics. Hữu ích khi app không đặt `http.route`.

Series cũ vẫn nằm trong Prometheus tới khi head block được cắt và hết retention; chúng không nhận mẫu mới nên thành stale.

## Chẩn đoán nhanh

1. `prometheus_tsdb_head_series` tăng theo traffic: dấu hiệu cardinality, không phải lượng mẫu.
2. `topk(10, count by (__name__) ({__name__=~".+"}))` chỉ ra `traces_span_metrics_*`.
3. `count(count by (url_path) (traces_span_metrics_calls_total))` xấp xỉ số request; các nhãn khác chỉ vài giá trị. Trang
   `Status → TSDB Status` của Prometheus liệt kê "Top label names with high value count" mà không cần viết query.

## Phòng lần sau

- Review cấu hình metric như review schema DB: mỗi nhãn mới cần trả lời "có bao nhiêu giá trị, có bị chặn không".
- Alert trên chính Prometheus: tốc độ tăng `prometheus_tsdb_head_series` (ví dụ `deriv(...[1h])` dương kéo dài) và số series mỗi job
  (`scrape_series_added`, `scrape_samples_scraped`).
- Giới hạn cứng ở scrape config: `sample_limit`, `label_value_length_limit`; vượt thì scrape đó fail (thấy ngay trên `up`) thay vì làm cả
  Prometheus OOM.
- Collector: `spanmetrics` có `aggregation_cardinality_limit` (giá trị vượt giới hạn gom vào một series `otel.metric.overflow`).
- Chi tiết theo từng request (đơn hàng nào, khách nào) thuộc về trace và log, nơi chi phí tỉ lệ với dữ liệu chứ không với số tổ hợp nhãn.
  Muốn đi từ metric tới request cụ thể thì dùng exemplar.
