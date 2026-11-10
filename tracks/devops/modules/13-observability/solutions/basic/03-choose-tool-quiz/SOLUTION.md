# Lời giải: trắc nghiệm chọn công cụ observability

| Câu | Đáp án | Giải thích ngắn |
| --- | --- | --- |
| logs-cheap-volume | b | Log đọc ít, lọc theo label và `trace_id`: Loki chỉ index label nên rẻ đĩa và RAM, chunk nén nằm trên object storage, query trong Grafana đã có. Elasticsearch index toàn văn tốn gấp nhiều lần cho một nhu cầu không dùng tới. Prometheus không lưu được nội dung log; nhãn chứa message làm nổ series |
| soc-full-text | c | Tìm chuỗi bất kỳ trên 12 tháng, rule phát hiện, điều tra: đúng thế mạnh của index toàn văn (Splunk, Elastic Security, OpenSearch Security Analytics). Loki `\|=` quét chunk nên chậm và tốn khi phạm vi rộng; Papertrail và Jaeger không làm SIEM |
| snmp-fleet | a | Thiết bị chỉ nói SNMP và VM không cài được exporter: Zabbix có template SNMP, auto-discovery, agent cho Windows, màn hình NOC. Không cài OTel SDK vào firmware được; đếm syslog không phải giám sát trạng thái |
| tiny-team-logs | b | Không ai vận hành, cần tail và tìm 7 ngày, alert theo chuỗi: một dịch vụ log SaaS nhỏ như Papertrail là đủ và rẻ. Cụm OpenSearch hay Graylog tự host là thêm việc vận hành cho team không có người làm |
| no-platform-team | b | Cần đủ APM, infra, log, RUM ngay mà không có người vận hành: SaaS như Datadog hay New Relic. Đổi lại là chi phí theo host, GB, user; nên gửi bằng OpenTelemetry để giữ đường lui. Tự dựng stack LGTM bản HA là một dự án riêng |
| pricing-users | c | New Relic tính theo GB ingest cộng phí mỗi "full platform user". Datadog tính chủ yếu theo host và theo từng sản phẩm. Người xem dashboard không tạo series hay span |
| self-host-log-ui | a | Graylog là sản phẩm quản lý log tự host có UI: input GELF/syslog, stream, pipeline, alert, phân quyền; lưu trên OpenSearch. Prometheus không giữ log; Jaeger lưu span chứ không phải log |
| avoid-lock-in | b | OpenTelemetry là chuẩn mở: SDK và OTLP không gắn vendor; Collector đổi exporter là đổi backend, gửi song song hai nơi khi chuyển. Agent độc quyền buộc sửa code hay cấu hình mọi service khi đổi |
| keep-errors-sampling | b | Chỉ khi trace đã xong mới biết nó lỗi hay chậm: tail sampling trong Collector (`tail_sampling` với policy status_code, latency, probabilistic). Head sampling 1% bỏ 99% trace lỗi. Mọi span của một trace phải tới cùng một Collector (dùng `loadbalancing` exporter theo trace id khi có nhiều Collector) |
| short-batch-job | c | Job ngắn hơn chu kỳ scrape: đẩy khi xong (Pushgateway, hay OTLP tới Collector), kèm metric dạng `last_success_timestamp_seconds` để alert khi job lâu không thành công. Giảm scrape toàn cục hay bắt job ngủ là chữa triệu chứng và tốn tài nguyên |
| page-worthy | d | Page theo **triệu chứng** người dùng thấy: khách không đặt được hàng. CPU cao mà người dùng không bị ảnh hưởng, một pod restart, đĩa còn ba tuần: ticket hay dashboard, không đánh thức ai |
| percentile-across-replicas | b | Quantile không cộng hay lấy trung bình được (trung bình của 10 p95 không phải p95). Histogram cộng bucket qua mọi replica rồi `histogram_quantile`, và tính lại cho cửa sổ bất kỳ |
| golden-signals | a, b, c, d | Latency, traffic, errors, saturation (sách Google SRE, chương 6). Uptime máy và tần suất deploy không thuộc bốn tín hiệu (tần suất deploy là chỉ số DORA) |
| pii-logs | a, b, c | Chặn từ nguồn là chính; Collector (`attributes`/`transform`/`redaction` processor) là lưới an toàn; retention theo loại dữ liệu và phân quyền query. Mã hoá đĩa không chặn người có quyền query; giữ lâu hơn làm khó việc xoá dữ liệu khách chứ không giúp |
