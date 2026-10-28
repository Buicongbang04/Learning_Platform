---
title: Data lake trên S3 bằng Terraform, tách môi trường
level: advanced
services: []
files:
  - path: starter/main.tf
    note: Nhiều TODO, bạn tự thiết kế
  - path: starter/variables.tf
    note: 2 TODO
  - path: starter/outputs.tf
    note: 1 TODO
  - path: tests/test_terraform_data_lake.py
    note: Không sửa. Chạy thêm terraform validate nếu máy có terraform
run:
  - uv run pytest tracks/data-engineer/modules/08-devops-for-data/exercises/advanced/01-terraform-data-lake -q
  - cd tracks/data-engineer/modules/08-devops-for-data/exercises/advanced/01-terraform-data-lake/starter && terraform init -backend=false && terraform validate
---

## Mục tiêu

Dùng Infrastructure as Code để dựng hạ tầng lưu trữ cho data lake Olist theo chuẩn bảo mật và
vận hành, dùng lại được cho nhiều môi trường mà không sửa code.

## Đề bài

Viết cấu hình Terraform (chạy được với OpenTofu) trong `starter/` tạo data lake trên AWS S3:

- Hai vùng lưu trữ `raw` và `curated`, mỗi vùng một bucket, tên có hậu tố môi trường
  (vd. `olist-raw-staging`). Có thể dùng `for_each` để không lặp code.
- Mỗi bucket: bật **versioning**, **mã hoá phía server** (SSE-S3 `AES256` hoặc `aws:kms`), **chặn
  public access** đủ 4 cờ, và **lifecycle rule** (vd. bucket raw chuyển sang `STANDARD_IA` sau 30
  ngày, xoá phiên bản cũ sau 90 ngày).
- Biến `environment` có `validation` chỉ nhận `dev`, `staging`, `prod`. Biến `region` có mặc định.
- Tag chung (`project`, `environment`, `managed_by`) định nghĩa một lần trong `locals` và áp cho mọi
  bucket (qua `tags = local.tags` hoặc `default_tags` của provider).
- Khối `terraform {}` khai báo `required_version` và provider `hashicorp/aws` có ràng buộc phiên bản.
- `outputs.tf` xuất tên (hoặc ARN) của cả hai bucket.
- Không viết access key/secret key trong code; credential lấy từ môi trường/OIDC.

Không cần tài khoản AWS: test kiểm tra cấu trúc tệp. Nếu máy có `terraform`, test chạy thêm
`terraform init -backend=false` và `terraform validate` (cần mạng để tải provider; không có thì skip).

## Tiêu chí đạt

- Có `terraform { required_version ... required_providers { aws = { source = "hashicorp/aws", version = ... } } }`.
- `variable "environment"` có khối `validation` nhắc tới `dev`, `staging`, `prod`.
- `locals` có map tag chứa `environment`, và bucket dùng `local.tags` (hoặc provider có `default_tags`).
- Có resource `aws_s3_bucket` cho cả `raw` và `curated`, tên bucket phụ thuộc `var.environment`.
- Có `aws_s3_bucket_versioning` (`Enabled`), `aws_s3_bucket_server_side_encryption_configuration`,
  `aws_s3_bucket_public_access_block` (4 cờ `true`), `aws_s3_bucket_lifecycle_configuration`.
- `outputs.tf` có ít nhất 2 output tham chiếu tới bucket.
- Không có `access_key`/`secret_key` trong code.
- `terraform validate` thành công (nếu chạy được).

## Gợi ý

### Gợi ý 1

Từ AWS provider v4, cấu hình versioning, encryption, lifecycle tách thành resource riêng
(`aws_s3_bucket_versioning`…) tham chiếu `bucket = aws_s3_bucket.this[each.key].id`, thay vì khối
lồng trong `aws_s3_bucket`.

### Gợi ý 2

```hcl
locals {
  zones = toset(["raw", "curated"])
}
resource "aws_s3_bucket" "this" {
  for_each = local.zones
  bucket   = "olist-${each.key}-${var.environment}"
}
```

Các resource phụ cũng `for_each = aws_s3_bucket.this` và dùng `each.value.id`.
