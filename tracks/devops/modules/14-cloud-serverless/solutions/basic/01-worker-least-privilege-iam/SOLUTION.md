# Lời giải: IAM least privilege cho worker Olist Shop

Lời giải nằm trong `infra/main.tf`; `versions.tf`, `variables.tf`, `outputs.tf` giữ như starter.

## Các quyết định

- **Trust policy là nửa còn lại của quyền.** Permission policy nói role làm được gì; trust policy nói ai được trở thành role. Starter
  tin cả `ec2.amazonaws.com`: bất kỳ EC2 instance nào trong tài khoản gắn được role này qua instance profile và có ngay quyền của worker.
  Lời giải chỉ tin `ecs-tasks.amazonaws.com`.
- **Chống confused deputy.** Service principal là của AWS, dùng chung cho mọi khách hàng. Điều kiện `aws:SourceAccount` (và
  `aws:SourceArn` với `ArnLike` tới `arn:aws:ecs:<region>:<account>:*`) bảo đảm chỉ ECS đang làm việc cho chính tài khoản này mới assume
  được role, kể cả khi ai đó biết ARN của role.
- **Action liệt kê, không wildcard.** `sqs:ChangeMessageVisibility` cần để worker kéo dài thời gian giữ message khi job chạy lâu;
  `sqs:GetQueueAttributes` cho SDK và healthcheck. Worker không gửi message nên không có `sqs:SendMessage`; không đọc lại báo cáo nên không
  có `s3:GetObject`.
- **Resource đúng tới mức object.** `"${aws_s3_bucket.reports.arn}/revenue/*"`: một bug ghi đè `exports/` hay bucket khác bị chặn. Tránh
  `"${var.prefix}-reports*"` vì khớp cả bucket `...-reports-public`.
- **Boundary là trần cho cả đội.** Boundary cho phép SQS, S3, Secrets Manager trên tài nguyên mang tiền tố, không có IAM hay STS. Ở công
  ty thật, admin bắt mọi role do team tạo phải mang boundary này (điều kiện `iam:PermissionsBoundary` trong quyền `iam:CreateRole` của
  team): team tự viết policy cho service của mình mà không tự leo thang được.
- **`data "aws_iam_policy_document"` thay vì `jsonencode`.** Sinh JSON chuẩn, gộp statement, kiểm cú pháp lúc plan. `sid` giúp đọc policy
  trong console và trong log CloudTrail.

## Vì sao test không dùng simulator

LocalStack community có `SimulatePrincipalPolicy` (moto), nhưng kết quả sai với wildcard action và khi có `Deny`, và bản community không
thực thi IAM lúc gọi API. Parser trong test (khoảng 40 dòng) đủ cho phần cốt lõi của logic đánh giá: explicit deny thắng, cần ít nhất
một allow, giao với boundary. Nó bỏ qua `Condition`, resource-based policy, SCP, session policy; trên AWS thật dùng IAM Policy Simulator
và IAM Access Analyzer (tìm quyền chưa dùng, tạo policy từ CloudTrail).

## Đọc thêm

- Trên ECS có hai role: **task role** (code của bạn dùng, bài này) và **task execution role** (ECS agent dùng để kéo image, đọc secret
  đưa vào biến môi trường, ghi log). Đừng gộp làm một.
- Muốn biết role thật sự dùng những quyền nào: bật CloudTrail, dùng "Generate policy" của IAM Access Analyzer sau một tuần chạy.
