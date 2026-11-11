---
title: IAM least privilege cho worker Olist Shop trên ECS
level: basic
services: [localstack-devops]
files:
  - path: starter/infra/main.tf
    note: 3 TODO (trust policy, permission policy, permissions boundary)
  - path: starter/infra/versions.tf
    note: Giữ nguyên
  - path: starter/infra/variables.tf
    note: Giữ nguyên
  - path: starter/infra/outputs.tf
    note: Giữ nguyên
  - path: tests/test_worker_iam.py
    note: Không sửa; apply trên localstack-devops rồi đánh giá policy bằng parser trong test
run:
  - docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
  - uv run pytest tracks/devops/modules/14-cloud-serverless/exercises/basic/01-worker-least-privilege-iam -q -rs
---

## Mục tiêu

Viết một IAM role đúng nghĩa least privilege: ai được đeo role (trust policy), role được làm gì (permission policy), và trần quyền
không ai vượt được kể cả khi policy sau này bị nới (permissions boundary). Kiểm bằng cách đánh giá policy thật sau khi apply.

## Đề bài

Worker của Olist Shop chuyển lên AWS, chạy trên ECS Fargate. Nó lấy job từ SQS, ghi báo cáo doanh thu vào S3 và đọc mật khẩu Postgres
từ Secrets Manager. `starter/infra/main.tf` đã tạo ba tài nguyên đó (tên theo `var.prefix`) và một role cấp quá rộng. Sửa ba TODO:

| Worker cần | Trên tài nguyên |
| --- | --- |
| `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:ChangeMessageVisibility`, `sqs:GetQueueAttributes` | Hàng đợi `aws_sqs_queue.jobs` |
| `s3:PutObject` | Chỉ các object dưới `revenue/` của bucket `aws_s3_bucket.reports` |
| `secretsmanager:GetSecretValue` | Đúng secret `aws_secretsmanager_secret.db` |

1. **Trust policy** (`data.aws_iam_policy_document.trust`): chỉ principal service `ecs-tasks.amazonaws.com` được `sts:AssumeRole`, kèm
   điều kiện `StringEquals` `aws:SourceAccount` bằng ID tài khoản (lấy từ `data.aws_caller_identity`). Có thể thêm `ArnLike`
   `aws:SourceArn`.
2. **Permission policy** (`data.aws_iam_policy_document.worker`): đúng bảng trên, liệt kê từng action (không `*` hay `?` trong tên action,
   kể cả `s3:Put*`), không `Resource = "*"`, không `NotAction`, `NotResource`, không `Condition` (parser của test không đánh giá
   Condition).
3. **Permissions boundary**: một `aws_iam_policy` tên `"${var.prefix}-worker-boundary"` gắn vào `permissions_boundary` của role.
   Boundary cho phép đủ những gì worker cần, nhưng chỉ trên tài nguyên mang tiền tố `var.prefix`, và không cho bất kỳ hành động IAM hay
   STS nào. Không cần `Condition`.

**Cách test chấm.** Qua `TofuLab`, test chạy `tofu init` và `tofu apply` trên `localstack-devops`, đọc lại role, inline policy, managed
policy gắn kèm và boundary bằng API IAM của LocalStack, rồi đánh giá từng cặp (hành động, ARN) bằng một parser policy viết trong test: khớp
wildcard `*` và `?`, action không phân biệt hoa thường, `Deny` thắng `Allow`, quyền hiệu lực là giao của identity policy và boundary. Test
kiểm 6 việc worker phải làm được, 21 việc không được làm (gửi message, xoá hàng đợi, đọc báo cáo, ghi ngoài `revenue/`, đổi ACL, bucket
tên gần giống, secret khác, `iam:PassRole` và `sts:AssumeRole` trên ARN role cụ thể, `kms:Decrypt` trên ARN key và alias...), trust policy
và boundary (thử IAM, STS và tài nguyên ngoài tiền tố trên ARN cụ thể). Mỗi phép kiểm đánh giá trên ARN thật, không trên `"*"`, và có test
đột biến chứng minh bộ kiểm bắt được policy lỏng (thêm `iam:PassRole` trên `role/*`, boundary `Allow *` trên `arn:aws:*:*:*:*`...).

**Giới hạn của cách chấm.** LocalStack bản community có `iam:SimulatePrincipalPolicy` nhưng đã kiểm ngày 2026-11-11 trên 4.4.0: không hiểu
wildcard trong action (`sqs:Receive*` bị báo deny), sai khi có statement `Deny` ở resource khác, không có `SimulateCustomPolicy`, và
LocalStack community không thực thi IAM khi gọi API. Vì vậy test không dùng simulator mà dùng parser tĩnh. Parser không đánh giá
`Condition`, policy variable (`${aws:username}`), resource-based policy, SCP hay session policy. Trên AWS thật, kiểm lại bằng IAM Policy
Simulator hay `aws iam simulate-principal-policy` và IAM Access Analyzer.

## Tiêu chí đạt

- `tofu apply` trên LocalStack thành công.
- Trust policy chỉ tin `ecs-tasks.amazonaws.com` trong đúng tài khoản.
- Worker làm được đúng 6 việc trong bảng; mọi việc ngoài bảng mà test thử đều bị từ chối.
- Role có permissions boundary `"${var.prefix}-worker-boundary"`, boundary không cho IAM, STS hay tài nguyên ngoài tiền tố.

## Gợi ý

### Gợi ý 1

ARN của object S3 là `arn:aws:s3:::<bucket>/<key>`; `aws_s3_bucket.reports.arn` là ARN của bucket, nối thêm `/revenue/*`. Cẩn thận với
wildcard ở tên: `"${var.prefix}-reports*"` khớp cả bucket `...-reports-public`, và `"${var.prefix}-jobs*"` khớp cả hàng đợi khác.

### Gợi ý 2

Boundary không cấp quyền; nó chỉ là trần. Quyền hiệu lực là phần giao: một hành động phải được cả permission policy lẫn boundary cho phép
(và không bị `Deny` ở đâu). Viết boundary rộng hơn permission policy một chút (ví dụ `sqs:SendMessage` trên hàng đợi có tiền tố) vẫn đúng,
vì permission policy không cho thì vẫn không làm được. ARN secret có hậu tố ngẫu nhiên 6 ký tự; dùng `aws_secretsmanager_secret.db.arn`.
