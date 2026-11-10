---
title: "Sự cố: Lambda báo giá vận chuyển hết giờ trong đợt khuyến mãi"
level: intermediate
services: []
files:
  - path: starter/handler/app.py
    note: Handler đang chạy ở production
  - path: starter/handler/shipping.py
    note: Client của dịch vụ báo giá (team khác viết), giữ nguyên
  - path: tests/test_freight_quotes.py
    note: Không sửa
  - path: tests/fixtures/quote_service.py
    note: Bản giả của dịch vụ báo giá, chạy trong container
run:
  - docker pull public.ecr.aws/lambda/python:3.12.2026.10.22.03@sha256:25aee9bac65f131c5d090d3e3a36ccf232d65cf3e6c1dbd0bffd43ca7ce34406
  - uv run pytest tracks/devops/modules/14-cloud-serverless/exercises/intermediate/02-incident-freight-quote-timeouts -q -rs
---

## Mục tiêu

Chẩn đoán và sửa một sự cố của Lambda xử lý event từ SQS chỉ từ triệu chứng, log và số liệu của dịch vụ phía sau; sửa sao cho hệ thống
vẫn đúng khi dịch vụ phía sau chậm hơn nữa.

## Đề bài

Lambda `freight-quotes` nhận đơn hàng mới từ hàng đợi SQS (batch tối đa 10 record, mỗi body `{"order_id": ..., ...}`), hỏi giá vận chuyển
từng đơn qua dịch vụ báo giá của team logistics (`shipping.quote(order_id)`), rồi trả `batchItemFailures`. Timeout của function là 3 giây.

Hợp đồng của dịch vụ báo giá: mỗi request mất khoảng 0,4 giây; một client mở quá 8 request cùng lúc thì nhận `429`; thỉnh thoảng một đơn trả
`500` vì hãng vận chuyển không trả lời.

Báo cáo từ người trực, tối thứ Sáu, ngày đầu đợt khuyến mãi:

- Trước đợt khuyến mãi mọi thứ bình thường: mỗi batch chỉ có một hai đơn.
- Từ 19:00, CloudWatch Logs của function đầy dòng `Task timed out after 3.00 seconds`; số lần invoke tăng gấp mấy lần số đơn mới.
- Team logistics phàn nàn: cùng một `order_id` bị hỏi giá 3, 4 lần; tải lên dịch vụ báo giá tăng vọt.
- DLQ của hàng đợi bắt đầu có đơn hoàn toàn hợp lệ.
- Một đơn bị hãng vận chuyển trả lỗi thì cả batch của nó bị đẩy lại.

`tests/fixtures/incident/` là bản sao của code production lúc đó. Sửa `starter/handler/app.py` (không sửa `shipping.py`) để:

- Batch 10 đơn hoàn tất trong timeout khi dịch vụ báo giá khoẻ, không record nào bị báo lỗi, mỗi đơn được hỏi giá đúng một lần, và không
  vi phạm hợp đồng của dịch vụ báo giá (không có `429`).
- Một đơn bị trả `500` chỉ làm record đó vào `batchItemFailures`.
- Khi dịch vụ báo giá chậm hẳn (1,8 giây mỗi request), handler vẫn trả lời trước timeout: đơn đã báo giá xong không bị đẩy lại, đơn chưa
  kịp thì nằm trong `batchItemFailures` để SQS giao lại sau.

**Cách test chấm.** Dịch vụ báo giá giả (`tests/fixtures/quote_service.py`) chạy trong container của `DockerLab`, đếm số lần hỏi giá mỗi
đơn, số request đồng thời cao nhất và số `429`; test đổi độ trễ và đơn lỗi qua API riêng của nó. Handler chạy trong `LambdaLab` (image
Lambda Python 3.12 thật, timeout 3 giây) trên cùng network của lab (`isolated=False`) để gọi được `http://quotes:8080`. Một test chạy
bản sự cố trong `tests/fixtures/incident/` để chứng minh nó tái hiện đúng triệu chứng. Cả bài chạy khoảng 15 giây.

## Tiêu chí đạt

- Test pass, kể cả test tái hiện sự cố.
- Giải thích được vì sao số lần invoke và số lần hỏi giá tăng gấp nhiều lần số đơn, và vì sao đơn hợp lệ rơi vào DLQ.
- Viết được 3 dòng "hành động phòng ngừa" cho postmortem (cảnh báo, giới hạn, kiểm thử).

## Gợi ý

### Gợi ý 1

Đọc log của function (`fn.logs()` trong test, hay CloudWatch Logs ở AWS thật) cùng số liệu của dịch vụ báo giá
(`curl http://127.0.0.1:<cổng>/stats` khi container đang chạy). Đo một lần invoke với 1 đơn, 5 đơn, 10 đơn: thời gian tăng theo quy luật
nào, so với timeout?

### Gợi ý 2

Khi một lần invoke hết giờ, Lambda không trả `batchItemFailures` nào: với event source mapping, cả batch được coi là thất bại. Những đơn
trong batch đó đã báo giá xong thì sao? `context.get_remaining_time_in_millis()` cho biết lần invoke còn bao nhiêu thời gian.
