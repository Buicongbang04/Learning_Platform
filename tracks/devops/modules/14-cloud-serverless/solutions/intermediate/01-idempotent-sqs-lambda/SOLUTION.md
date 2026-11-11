# Lời giải: Lambda xử lý payment idempotent, có DLQ

Lời giải: `handler/app.py`, `infra/queues.tf`, `infra/lambda.tf`.

## Code

- **Idempotency bằng transaction có điều kiện.** `transact_write_items` gồm `Put` bản ghi `payment_id` (điều kiện
  `attribute_not_exists`) và `Update ADD` vào ledger. Hai việc thành công cùng nhau hoặc không việc nào xảy ra, nên không có cửa sổ "đã
  ghi marker mà chưa cộng tiền" hay ngược lại. Hai Lambda cùng nhận một payment song song: một transaction thắng, cái kia nhận
  `ConditionalCheckFailed` và trả `False`.
- **Khoá nghiệp vụ, không phải `messageId`.** Producer gửi lại tạo message mới; `messageId` khác nhau nhưng cùng `payment_id`.
- **Bản ghi chống trùng có hạn.** `expires_at` cộng TTL của bảng xoá bản ghi sau 7 ngày (DynamoDB xoá trễ tới vài ngày, không tốn WCU).
  Cửa sổ 7 ngày phải dài hơn thời gian một message có thể quay lại (retention của hàng đợi 4 ngày, cộng DLQ redrive).
- **Partial batch response.** Mỗi record trong `try` riêng; lỗi thì thêm `messageId` vào `batchItemFailures`. Lambda trả thành công,
  event source mapping xoá các message còn lại và chỉ để record lỗi quay lại. Không bật `ReportBatchItemFailures` ở mapping thì giá trị
  trả về bị bỏ qua và mọi message được xoá: đó là lý do test kiểm cả hai phía.
- **Kiểm kiểu chặt.** `type(amount) is not int` loại cả `True` (bool là int trong Python), `10.5` và `"1000"`. Tiền tính bằng số nguyên
  xu, không float.
- **Client tạo ở ngoài handler.** `boto3.client` tạo lúc nạp module, dùng lại giữa các lần invoke trong cùng môi trường thực thi: giảm
  thời gian mỗi lần gọi, chỉ tốn ở cold start.
- `IAM`: `TransactWriteItems` không phải một action IAM riêng; cần `dynamodb:PutItem` trên bảng idempotency và `dynamodb:UpdateItem` trên
  bảng ledger.

## Hạ tầng

- **Visibility timeout ≥ 6 lần timeout của function** (khuyến nghị của AWS cho event source mapping): mapping có thể giữ message trong lúc
  gom batch và retry nội bộ; visibility ngắn hơn thời gian xử lý thì message hiện lại cho lần nhận khác giữa chừng.
- **DLQ sau 3 lần nhận**, giữ 14 ngày (tối đa), dài hơn 4 ngày của hàng đợi nguồn: với hàng đợi standard, tuổi message tính từ lúc vào
  hàng đợi nguồn, DLQ giữ ngắn hơn thì message có thể hết hạn ngay khi vừa sang.
- **`maximum_concurrency`** giới hạn số Lambda đồng thời đọc hàng đợi này (2..1000), bảo vệ DynamoDB, downstream và hoá đơn mà không
  dùng reserved concurrency của cả function.
- `aws_sqs_queue_redrive_allow_policy` (chỉ cho hàng đợi `payments` dùng DLQ này) nên có ở production. Bài không dùng vì với provider
  6.12.0 trên LocalStack 4.4.0, xoá tài nguyên đó treo tới hết timeout.

## Đọc thêm

- Powertools for AWS Lambda (Python) có sẵn `idempotent` decorator và `BatchProcessor` làm đúng hai việc của bài, kèm trạng thái
  `INPROGRESS` cho trường hợp function chết giữa chừng.
- Hàng đợi FIFO có `MessageDeduplicationId` chống trùng trong 5 phút ở phía SQS, nhưng không thay được idempotency ở consumer.
