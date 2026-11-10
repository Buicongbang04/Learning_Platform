# Runbook: lab serverless Olist Shop trên AWS thật

Chủ runbook: nhóm platform Olist Shop (người trực tuần này). Lần chạy gần nhất: 2026-11-11, tài khoản sandbox, us-east-1.

## 1. Chi phí ước tính

Giả định: region `us-east-1`, hạ tầng sống tối đa 1 ngày, khoảng 2 000 request thử qua API, mỗi request một message SQS và một lần
Lambda chạy 200 ms với 256 MB (arm64). Free Tier: Lambda (1 triệu request, 400 000 GB-giây mỗi tháng), SQS (1 triệu request), DynamoDB
(25 GB lưu trữ) là phần miễn phí vĩnh viễn; tài khoản tạo sau 15/7/2025 nhận credit thay cho Free Tier 12 tháng cũ (API Gateway 1 triệu
request), nên bảng dưới tính như thể không có Free Tier cho API Gateway.

| Tài nguyên | Đơn giá | Lượng dùng | Thành tiền |
| --- | --- | --- | --- |
| API Gateway REST | 3,50 USD / 1 triệu request | 2 000 request | 0,01 USD |
| Lambda arm64 | 0,0000133334 USD / GB-giây, 0,20 USD / 1 triệu request | 100 GB-giây, 2 000 request | 0,00 USD (Free Tier) |
| SQS standard | 0,40 USD / 1 triệu request | khoảng 10 000 request (gửi, nhận, xoá, poll) | 0,00 USD (Free Tier) |
| DynamoDB on-demand | 0,625 USD / 1 triệu write request unit | khoảng 8 000 WRU | 0,01 USD |
| CloudWatch Logs | 0,50 USD / GB ghi vào | dưới 0,01 GB | 0,01 USD |
| CloudWatch alarm | 0,10 USD / alarm / tháng | 1 alarm, 1 ngày | 0,00 USD (10 alarm đầu miễn phí) |

Tổng: khoảng 0,03 USD cho một ngày lab. Rủi ro chi phí không nằm ở bảng này mà ở thứ chạy không dừng: một vòng lặp gửi request vô
hạn (bị chặn bởi quota 1 000 request/ngày của usage plan và throttling 5 request/giây), Lambda bị gọi lại liên tục vì message hỏng (bị chặn
bởi DLQ sau 3 lần nhận), log giữ mãi (retention 7 ngày).

## 2. Budget và cảnh báo

- Budget `COST` hằng tháng 5 USD trong cấu hình (`aws_budgets_budget.monthly`), cảnh báo **ACTUAL** ở 50% và **FORECASTED** (dự báo)
  ở 100%, gửi email tới `alert_email`.
- Từ 30/9/2026 AWS Budgets gửi email xác minh tới địa chỉ mới; bấm link trước khi tin vào cảnh báo. Kiểm trên console Budgets: subscriber
  không còn `Pending`.
- Budget chậm tới vài giờ và chỉ cảnh báo, không tự tắt gì. Thứ dừng chi phí thật là tag `ExpiresOn`, quota của usage plan và bước dọn ở
  mục 5. Muốn giữ budget cho cả tài khoản sau khi dọn lab, đặt nó ở một stack riêng không destroy.
- Alarm `payments-dlq-not-empty`: DLQ có message là có payment không xử lý được, cần người xem (chưa gửi đi đâu trong lab; ở môi trường
  thật gắn SNS tới kênh trực).

## 3. Triển khai

Điều kiện: profile SSO `olist-sandbox` như hướng dẫn ở module 08 Advanced 02, permission set chỉ có Lambda, SQS, DynamoDB, API Gateway,
IAM (tạo role có tiền tố lab, `iam:PassRole` cho role đó), CloudWatch Logs và alarm, Budgets, trong `us-east-1`. Chạy từ `exercises/advanced/02-real-aws-serverless-runbook/starter/aws/`.

```bash
export AWS_PROFILE=olist-sandbox AWS_REGION=us-east-1 SANDBOX_ACCOUNT_ID=111122223333 &&
unset AWS_ENDPOINT_URL AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN &&
aws sso login &&
test "$(aws sts get-caller-identity --query Account --output text)" = "$SANDBOX_ACCOUNT_ID" &&
mkdir -p build &&
python3 -m zipfile -c build/payments-worker.zip \
  ../../../../intermediate/01-idempotent-sqs-lambda/starter/handler/app.py &&
printf 'prefix = "olist-sls-%s"\nowner = "%s"\nexpires_on = "%s"\nalert_email = "%s"\n' \
  "$USER" "you@example.com" "$(date -d '+1 day' +%F)" "you@example.com" > lab.tfvars &&
tofu init &&
tofu plan -var-file=lab.tfvars -out=lab.tfplan
```

Đọc plan trước khi apply: chỉ có `create`; không có NAT gateway, EC2, RDS, provisioned concurrency; `memory_size = 256`,
`architectures = ["arm64"]`, `maximum_concurrency = 2`; usage plan có quota; tag `ExpiresOn` là ngày mai.

```bash
tofu show -json lab.tfplan | jq -r '.resource_changes[] | "\(.change.actions | join(",")) \(.address)"' &&
test "$(aws sts get-caller-identity --query Account --output text)" = "$SANDBOX_ACCOUNT_ID" &&
tofu apply lab.tfplan
```

## 4. Kiểm tra

```bash
URL="$(tofu output -raw invoke_url)" &&
KEY="$(aws apigateway get-api-key --api-key "$(tofu output -raw api_key_id)" --include-value --query value --output text)" &&
curl -fsS -X POST "$URL" -H "x-api-key: $KEY" -H 'Content-Type: application/json' \
  -d '{"payment_id": "pay-lab-1", "seller_id": "3442f8959a84dea7ee197c632cb2df15", "amount_cents": 12990}' &&
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$URL" -H 'Content-Type: application/json' -d '{}' &&
sleep 10 &&
aws dynamodb get-item --table-name "olist-sls-$USER-seller-ledger" \
  --key '{"seller_id": {"S": "3442f8959a84dea7ee197c632cb2df15"}}' &&
aws sqs get-queue-attributes --queue-url "$(tofu output -raw dlq_url)" --attribute-names ApproximateNumberOfMessages
```

Kỳ vọng: lần gọi có key trả `{"accepted": true}`, lần không key trả `403`; ledger có `balance_cents = 12990`; DLQ có 0 message. Gửi lại
cùng `payment_id` thì balance không đổi (idempotency từ bài Intermediate 01). Không in `KEY` ra log hay chat; nó chỉ sống trong shell này.

## 5. Dọn dẹp

Cùng ngày, kể cả khi lab hỏng giữa chừng:

```bash
test "$(aws sts get-caller-identity --query Account --output text)" = "$SANDBOX_ACCOUNT_ID" &&
tofu destroy -var-file=lab.tfvars &&
aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'olist-sls-$USER')].FunctionName" --output text &&
aws sqs list-queues --queue-name-prefix "olist-sls-$USER" --output text &&
aws apigateway get-rest-apis --query "items[?starts_with(name, 'olist-sls-$USER')].id" --output text &&
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/olist-sls-$USER" --query 'logGroups[].logGroupName' --output text &&
rm -f lab.tfplan lab.tfvars build/payments-worker.zip
```

Bốn lệnh `aws` phải in rỗng. Log group do Lambda tự tạo khi chạy trước khi tofu tạo log group thì không nằm trong state: xoá tay bằng
`aws logs delete-log-group`. Hôm sau mở Cost Explorer, lọc tag `Project = olist-serverless-lab`: không còn phát sinh.

## 6. Bản chạy local tương đương

Không có tài khoản AWS thì làm đúng luồng này trên máy: bài Intermediate 01 chạy handler trong `LambdaLab` (image Lambda Python thật với
Runtime Interface Emulator), hàng đợi, DLQ và bảng DynamoDB trên `localstack-devops` bằng `tofu apply`, phần Lambda và event source mapping
kiểm bằng `tofu plan`. Test của bài này cũng chỉ chạy `tofu plan` cấu hình `aws/` trên LocalStack, không bao giờ gọi AWS thật.

## 7. Khi có sự cố

- Chi phí tăng bất thường: chặn nguồn gọi trước, rồi tắt người xử lý, rồi mới điều tra; cuối cùng `tofu destroy`:

  ```bash
  API_ID="$(aws apigateway get-rest-apis --query "items[?name=='olist-sls-$USER-payments'].id" --output text)" &&
  aws apigateway update-stage --rest-api-id "$API_ID" --stage-name lab \
    --patch-operations 'op=replace,path=/*/*/throttling/rateLimit,value=0' 'op=replace,path=/*/*/throttling/burstLimit,value=0' &&
  ESM="$(aws lambda list-event-source-mappings --function-name "olist-sls-$USER-payments-worker" --query 'EventSourceMappings[0].UUID' --output text)" &&
  aws lambda update-event-source-mapping --uuid "$ESM" --no-enabled
  ```
- DLQ có message: đọc message bằng `aws sqs receive-message` (không xoá), sửa handler hay dữ liệu, rồi redrive về hàng đợi chính bằng
  `aws sqs start-message-move-task`; đừng xoá DLQ để alarm im.
- `tofu apply` dở dang: không chạy lại `apply` mù; `tofu plan` để xem state, sửa, apply plan mới. State mất thì dọn theo tiền tố bằng các
  lệnh liệt kê ở mục 5.
- Lambda báo `AccessDeniedException`: so quyền trong policy của role với hành động trong log lỗi; không bao giờ "sửa nhanh" bằng `*`.
