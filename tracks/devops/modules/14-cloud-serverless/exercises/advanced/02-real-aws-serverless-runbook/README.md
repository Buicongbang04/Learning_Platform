---
title: Runbook lab serverless trên AWS thật (tuỳ chọn), kiểm bằng plan trên LocalStack
level: advanced
services: [localstack-devops]
files:
  - path: starter/aws/versions.tf
    note: Provider, thêm default_tags
  - path: starter/aws/variables.tf
    note: Thêm validation
  - path: starter/aws/main.tf
    note: Budget, log group, Lambda, event source mapping, alarm
  - path: starter/aws/api.tf
    note: API Gateway REST tới SQS, API key, usage plan, throttling
  - path: starter/aws/outputs.tf
    note: Output tuỳ bạn
  - path: starter/RUNBOOK.md
    note: Runbook 7 phần
  - path: tests/test_serverless_lab.py
    note: Không sửa; chỉ plan trên LocalStack, không bao giờ gọi AWS thật
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - uv run pytest tracks/devops/modules/14-cloud-serverless/exercises/advanced/02-real-aws-serverless-runbook -q -rs
---

## Mục tiêu

Đưa luồng payment của bài Intermediate 01 lên AWS thật một cách có trách nhiệm: hạ tầng có trần chi phí (budget, quota, throttling, giới hạn
đồng thời, retention), runbook mà người khác đọc là chạy được, kiểm được và dọn được. Không có tài khoản AWS thì làm phần cấu hình và runbook,
test kiểm bằng plan trên LocalStack.

## Đề bài

Luồng: client `POST /payments` (API Gateway REST, bắt API key) → integration kiểu `AWS` gửi thẳng body vào SQS `payments` (không có Lambda
ở cửa vào) → event source mapping → Lambda `payments-worker` (handler của bài Intermediate 01) → DynamoDB. Message hỏng sang DLQ, DLQ có
message thì alarm.

**Cấu hình** (`starter/aws/`, đã có phần lõi, sửa năm TODO):

- `default_tags`: `Project = "olist-serverless-lab"`, `Owner = var.owner`, `ExpiresOn = var.expires_on`.
- Validation: `expires_on` dạng `YYYY-MM-DD`; `monthly_budget_usd` trong (0, 10].
- `aws_budgets_budget` loại `COST`, `MONTHLY`, `USD`, ≤ 10, cảnh báo `ACTUAL` theo phần trăm ≤ 80 và `FORECASTED` ≤ 100 tới `var.alert_email`.
- Lambda `arm64`, memory ≤ 512 MB, timeout ≤ 30 giây; log group `/aws/lambda/<tên function>` retention 1..14 ngày; event source mapping có
  `ReportBatchItemFailures` và `maximum_concurrency` 2..5; visibility timeout của hàng đợi ≥ 6 lần timeout; bảng DynamoDB on-demand.
- `aws_cloudwatch_metric_alarm` trên `AWS/SQS` `ApproximateNumberOfMessagesVisible` của DLQ (dimension `QueueName` lấy từ hàng đợi DLQ),
  so sánh lớn hơn ngưỡng.
- API: mọi method `api_key_required = true`; integration chỉ kiểu `AWS`, `AWS_PROXY` hay `MOCK` (không proxy HTTP tới URL tuỳ ý); usage
  plan có quota theo ngày ≤ 5000 và gắn API key; `aws_api_gateway_method_settings` throttling rate ≤ 10, burst ≤ 20.
- Không NAT gateway, EC2, RDS, Elastic IP, load balancer, HTTP API v2, provisioned concurrency.

**Runbook** (`starter/RUNBOOK.md`, giữ bảy tiêu đề `## 1.` tới `## 7.`):

| Phần | Test kiểm |
| --- | --- |
| 1. Chi phí ước tính | Bảng ≥4 dòng đủ 4 cột (`Tài nguyên`, `Đơn giá`, `Lượng dùng`, `Thành tiền`); dòng `Tổng ... <số> USD` ≤ 5; nói Free Tier có áp dụng không |
| 2. Budget và cảnh báo | Nhắc budget, cảnh báo dự báo (forecast), email |
| 3. Triển khai | Khối lệnh có `aws sts get-caller-identity`, `tofu plan ... -out=<tệp>`, `tofu apply <tệp>.tfplan`; không `-auto-approve` |
| 4. Kiểm tra | Gọi API bằng `curl` có header `x-api-key` |
| 5. Dọn dẹp | Khối lệnh có `tofu destroy` và ≥2 lệnh `aws ... list-/describe-/get-` kiểm không còn tài nguyên |
| 6. Bản chạy local tương đương | Nhắc LocalStack hay LambdaLab |
| 7. Khi có sự cố | ≥3 gạch đầu dòng (chi phí tăng vọt, DLQ có message, apply dở dang...) |

**Chạy trên AWS thật (tuỳ chọn, không chấm).** Dùng tài khoản sandbox riêng và credential ngắn hạn qua IAM Identity Center như bài Advanced
02 của module 08 (profile `olist-sandbox`, kiểm đúng tài khoản trước mỗi lệnh ghi). Cài AWS CLI v2 theo mục 0 của README module. Đóng gói
handler của bài Intermediate 01 thành `build/payments-worker.zip` (`python3 -m zipfile -c build/payments-worker.zip <đường dẫn>/app.py`).
Ước tính chi phí một ngày lab là vài xu nếu làm đúng runbook; khoản rủi ro là quên dọn. Dọn trong ngày.

**Cách test chấm (bản local).** Test không bao giờ gọi AWS thật: `TofuLab` chạy `tofu init` và `tofu plan -out` + `show -json` trên
`localstack-devops` với `ci.auto.tfvars.json` (owner, `expires_on`, `alert_email` giả), không apply. LocalStack community không có Budgets,
CloudWatch hay chạy Lambda, nhưng plan tạo mới không gọi API của chúng. `tofu plan` với `-var` sai để kiểm validation. Runbook được kiểm
khung, rồi bộ kiểm chạy trên hai fixture (khung trống, bản yếu) để chứng minh bắt được lỗi. Bản chạy được trên máy của cùng luồng là bài
Intermediate 01. Cả bài chạy khoảng 30 giây.

## Tiêu chí đạt

- Test pass.
- Rubric trong `solutions/advanced/02-real-aws-serverless-runbook/SOLUTION.md` đạt từ 7/10.
- (Tự đánh giá) Nếu chạy thật: email xác minh của Budgets đã bấm; gọi không có key bị `403`; hôm sau Cost Explorer lọc theo tag
  `Project = olist-serverless-lab` không còn phát sinh.

## Gợi ý

### Gợi ý 1

Integration SQS của API Gateway REST: `type = "AWS"`, `uri = "arn:aws:apigateway:<region>:sqs:path/<account>/<tên hàng đợi>"`,
`credentials` là role cho `apigateway.amazonaws.com` chỉ có `sqs:SendMessage` trên hàng đợi đó, header
`Content-Type: application/x-www-form-urlencoded` và request template `Action=SendMessage&MessageBody=$util.urlEncode($input.body)`.
Throttling ở stage đặt bằng `aws_api_gateway_method_settings` với `method_path = "*/*"`.

### Gợi ý 2

Trần chi phí của lab nằm ở nhiều chỗ: quota usage plan chặn số request mỗi ngày, throttling chặn tốc độ, `maximum_concurrency` chặn số
Lambda, DLQ chặn vòng retry vô hạn, retention chặn log, budget chỉ báo (chậm vài giờ, không tự tắt gì). Runbook tốt cho biết cách tắt
từng van khi có sự cố trước khi điều tra.
