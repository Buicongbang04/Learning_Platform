---
title: Lambda xử lý payment từ SQS, idempotent, có DLQ
level: intermediate
services: [localstack-devops]
files:
  - path: starter/handler/app.py
    note: 3 TODO (kiểm payload, cộng tiền một lần, báo lỗi từng message)
  - path: starter/infra/queues.tf
    note: 2 TODO (DLQ và visibility timeout, TTL)
  - path: starter/infra/lambda.tf
    note: 2 TODO (policy của worker, event source mapping)
  - path: starter/infra/variables.tf
    note: Giữ nguyên
  - path: starter/infra/versions.tf
    note: Giữ nguyên
  - path: starter/infra/outputs.tf
    note: Giữ nguyên
  - path: tests/test_payments_worker.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - docker pull public.ecr.aws/lambda/python:3.12.2026.10.22.03@sha256:25aee9bac65f131c5d090d3e3a36ccf232d65cf3e6c1dbd0bffd43ca7ce34406
  - uv run pytest tracks/devops/modules/14-cloud-serverless/exercises/intermediate/01-idempotent-sqs-lambda -q -rs
---

## Mục tiêu

Viết một consumer SQS đúng kiểu Lambda: cùng một payment đến hai lần chỉ cộng tiền một lần, một message hỏng không kéo cả batch chạy
lại, message hỏng mãi thì sang DLQ thay vì quay vòng tới hết hạn. Hạ tầng bằng OpenTofu, code chạy trong container Lambda thật.

## Đề bài

Cổng thanh toán đẩy event "payment đã xác nhận" vào hàng đợi SQS `payments`; mỗi message là JSON
`{"payment_id": "pay-...", "seller_id": "...", "amount_cents": 12990}`. Lambda `payments-worker` cộng `amount_cents` vào số dư của seller
trong bảng DynamoDB `seller-ledger` (thuộc tính `balance_cents`, và `payments` đếm số payment). SQS là at-least-once: cùng một message có
thể tới hai lần, và cổng thanh toán đôi khi gửi lại cùng `payment_id` trong một message mới.

**Code** (`starter/handler/app.py`, chỉ thư viện chuẩn và `boto3` có sẵn trong image Lambda):

1. `parse`: body không phải JSON object, thiếu `payment_id`/`seller_id` (chuỗi khác rỗng), hay `amount_cents` không phải số nguyên
   dương (kể cả `10.5`, `"1000"`) thì ném `InvalidPayment`.
2. `credit`: cùng một `payment_id` chỉ cộng tiền một lần, kể cả khi hai lần gọi chạy song song. Ghi `payment_id` vào bảng
   `payment-idempotency` (kèm `expires_at` = bây giờ + 7 ngày, epoch giây) và cộng tiền **trong cùng một transaction** DynamoDB. Trả
   `False` khi payment đã ghi trước đó.
3. `handler`: trả `{"batchItemFailures": [{"itemIdentifier": <messageId>}, ...]}` chỉ gồm record lỗi; record hợp lệ trong cùng batch vẫn
   được xử lý; payment trùng không phải lỗi.

**Hạ tầng** (`starter/infra/`, provider ghim 6.12.0, mọi tên theo `var.prefix`):

4. `aws_sqs_queue.payments` có `redrive_policy` tới `aws_sqs_queue.payments_dlq`, `maxReceiveCount` trong 2..5, và
   `visibility_timeout_seconds` ít nhất 6 lần timeout của Lambda (`var.function_timeout`). DLQ giữ message lâu hơn hàng đợi nguồn.
5. `aws_dynamodb_table.idempotency` bật TTL theo thuộc tính `expires_at`.
6. Policy của role worker chỉ gồm hành động cần thiết trên đúng hàng đợi, hai bảng và log group của function; không `*`.
7. `aws_lambda_event_source_mapping.payments` bật `ReportBatchItemFailures`, `batch_size` ≤ 10, `scaling_config.maximum_concurrency`
   trong 2..20.

Giữ nguyên tên tài nguyên và bốn output (`queue_url`, `dlq_url`, `ledger_table`, `idempotency_table`).

**Cách test chấm.** Qua `TofuLab`: `tofu plan` toàn bộ cấu hình (kiểm Lambda, event source mapping, hàng đợi), rồi `tofu apply
-exclude=aws_lambda_function.worker -exclude=aws_lambda_event_source_mapping.payments` lên `localstack-devops`: hàng đợi, DLQ, bảng, role
được tạo thật. Function Lambda không apply vì LocalStack của track không chạy Lambda (cần socket Docker); thay vào đó `LambdaLab` chạy
`handler/` trong image Lambda Python 3.12 của AWS (ghim digest, có Runtime Interface Emulator), code gọi DynamoDB trên LocalStack với
credential giả. Test đóng vai event source mapping: tạo event dạng SQS, gửi batch trùng, batch có record hỏng, và với hàng đợi thật thì
nhận, invoke, xoá record thành công, để message hỏng quay lại tới khi SQS chuyển nó sang DLQ. Tạo hàng đợi bằng provider 6.12.0 mất khoảng
25 giây mỗi hàng đợi (provider chờ thuộc tính lan truyền); cả bài chạy khoảng 1,5 phút.

## Tiêu chí đạt

- Gửi một batch có payment trùng, rồi gửi lại: seller được cộng đúng mỗi payment một lần.
- Batch có 4 record hỏng lẫn 1 record đúng: `batchItemFailures` đúng 4 record hỏng, record đúng vẫn được cộng.
- Message hỏng sang DLQ sau `maxReceiveCount` lần nhận; message đúng cộng một lần, hàng đợi rỗng.
- Plan: DLQ, visibility timeout, TTL, `ReportBatchItemFailures`, `maximum_concurrency`, policy không `*`.

## Gợi ý

### Gợi ý 1

`dynamodb.transact_write_items` với hai mục: `Put` vào bảng idempotency có `ConditionExpression: "attribute_not_exists(payment_id)"`, và
`Update` bảng ledger với `ADD balance_cents :amount, payments :one`. Điều kiện sai thì cả transaction bị huỷ: `ClientError` mã
`TransactionCanceledException`, `error.response["CancellationReasons"][0]["Code"] == "ConditionalCheckFailed"`.

### Gợi ý 2

Không dựa vào `messageId` để chống trùng: message gửi lại có `messageId` mới. Khoá idempotency là khoá nghiệp vụ (`payment_id`). Trong
`handler`, bắt lỗi theo từng record (`try` trong vòng lặp), đừng để một exception thoát ra: Lambda lỗi cả lần gọi thì cả batch quay lại
hàng đợi, kể cả những payment đã cộng xong.
