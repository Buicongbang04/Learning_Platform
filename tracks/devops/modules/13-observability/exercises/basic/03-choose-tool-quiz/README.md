---
title: Trắc nghiệm - chọn công cụ observability
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn đúng công cụ cho từng tình huống: Prometheus, Loki, Jaeger, OpenTelemetry hay ELK/OpenSearch, Graylog, Splunk, Papertrail, Datadog,
New Relic, Zabbix; và nhận ra alert nào đáng đánh thức người, sampling nào giữ được trace cần, cách xử lý PII trong log.

## Đề bài

Bài này không có code. Làm 14 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 12 câu chọn một đáp án, 2 câu chọn mọi đáp án
đúng. Đọc mục 1 tới 7 của module trước khi làm.

Với mỗi câu, tự hỏi:

1. **Dữ liệu trông thế nào**: số đo có nhãn, dòng sự kiện, hay cây span? Bao nhiêu mỗi ngày, giữ bao lâu, ai đọc?
2. **Ai vận hành**: có team platform không, hay cần thứ chạy sẵn và trả tiền theo dùng?
3. **Câu hỏi sẽ hỏi lúc sự cố**: "người dùng có bị ảnh hưởng không", "request này đi qua đâu", "chuỗi này xuất hiện ở đâu"?

## Tiêu chí đạt

- Đúng ít nhất 11/14 câu.
- Với mỗi câu sai, nói lại được vì sao đáp án đúng đúng, và trong tình huống nào phương án bạn chọn mới hợp.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Loki index nhãn, không index nội dung; Elasticsearch/OpenSearch và Splunk index toàn văn. Chi phí đi theo thứ được index. Zabbix mạnh ở
thiết bị và máy không cài được exporter; Prometheus mạnh ở service trên Kubernetes.

### Gợi ý 2

Head sampling quyết định ở span đầu tiên, trước khi biết request có lỗi hay chậm. Summary tính quantile ở từng instance và không cộng được;
histogram cộng được bucket.
