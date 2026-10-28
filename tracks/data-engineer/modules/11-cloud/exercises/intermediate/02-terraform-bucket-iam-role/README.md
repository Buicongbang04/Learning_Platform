---
title: Terraform cho bucket và IAM role của job Glue
level: intermediate
services: []
files:
  - path: starter/main.tf
    note: 5 TODO
  - path: tests/test_terraform_iam_role.py
    note: Không sửa. Chạy thêm terraform validate nếu máy có terraform/tofu
run:
  - uv run pytest tracks/data-engineer/modules/11-cloud/exercises/intermediate/02-terraform-bucket-iam-role -q
  - cd tracks/data-engineer/modules/11-cloud/exercises/intermediate/02-terraform-bucket-iam-role/starter && terraform init -backend=false && terraform validate
---

## Mục tiêu

Module 08 đã dựng bucket bằng Terraform. Bài này đi tiếp phần mà người mới hay bỏ qua: **danh
tính của workload**. Bạn tạo một IAM role cho job AWS Glue, với trust policy (ai được "đội" role)
và permission policy least-privilege trỏ đúng vào bucket vừa tạo, không dùng access key tĩnh.

## Đề bài

Viết `starter/main.tf` (một tệp, chạy được với Terraform hoặc OpenTofu):

1. **TODO 1** Khối `terraform {}` có `required_version` và provider `hashicorp/aws` có ràng buộc
   `version`. Biến `environment` (string) và `region` (có `default`).
2. **TODO 2** `aws_s3_bucket` tên `olist-lake-${var.environment}` kèm
   `aws_s3_bucket_public_access_block` bật đủ 4 cờ (phần này đã học ở module 08, viết ngắn).
3. **TODO 3** `aws_iam_role` cho Glue: `assume_role_policy` (viết bằng `jsonencode(...)` hoặc
   `data "aws_iam_policy_document"`) cho phép principal **service** `glue.amazonaws.com` thực hiện
   `sts:AssumeRole`. Không được cho principal `"*"` hay `"AWS": "*"`.
4. **TODO 4** Permission policy (`aws_iam_policy` + `aws_iam_role_policy_attachment`, hoặc
   `aws_iam_role_policy`) cho phép:
   - `s3:GetObject` trên `<arn bucket>/raw/*`;
   - `s3:PutObject` trên `<arn bucket>/curated/*`;
   - `s3:ListBucket` trên chính ARN bucket.

   ARN phải tham chiếu resource (`aws_s3_bucket.<tên>.arn`), không gõ cứng. Không dùng action
   `"*"`/`"s3:*"`, không dùng resource `"*"`.
5. **TODO 5** Gắn thêm managed policy `arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole`
   (quyền log/catalog cơ bản của Glue) bằng `aws_iam_role_policy_attachment`, và `output` ARN của role.

Không cần tài khoản AWS: test kiểm tra cấu trúc. Muốn `apply` thử không tốn tiền, dùng LocalStack
(`docker compose -f setup/docker-compose.yml up -d localstack`) với `tflocal` hoặc provider có
`endpoints { s3 = "http://localhost:4566" ... }` (xem SOLUTION.md).

## Tiêu chí đạt

- Có `terraform {}` với `required_version` và provider `hashicorp/aws` có version; có biến `environment`, `region` (default).
- Bucket tên phụ thuộc `var.environment`, có public access block 4 cờ `true`.
- `aws_iam_role` có trust policy service `glue.amazonaws.com` + `sts:AssumeRole`, không principal `*`.
- Permission policy có `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`, tham chiếu `aws_s3_bucket.*.arn`
  với `/raw/*` và `/curated/*`, không wildcard rộng.
- Có attachment tới `AWSGlueServiceRole`, có `output` tham chiếu `aws_iam_role`.
- Không có `access_key`/`secret_key`/`aws_iam_access_key`/`aws_iam_user` trong code.
- `terraform validate` thành công (nếu chạy được).

## Gợi ý

### Gợi ý 1

```hcl
resource "aws_iam_role" "glue_etl" {
  name = "olist-glue-etl-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}
```

### Gợi ý 2

Trong `jsonencode`, ghép chuỗi ARN bằng interpolation: `"${aws_s3_bucket.lake.arn}/raw/*"`.
`s3:ListBucket` dùng `aws_s3_bucket.lake.arn` (không có `/*`).
