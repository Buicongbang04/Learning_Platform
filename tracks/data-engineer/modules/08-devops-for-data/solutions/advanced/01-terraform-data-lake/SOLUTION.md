# Hướng giải: data lake S3 bằng Terraform

Bài này không có một đáp án duy nhất. Dưới đây là hướng làm, các quyết định cần cân nhắc, một bản
tham khảo (đã qua bộ test) và rubric chấm.

## Hướng làm

1. Khai báo `terraform {}` với `required_version` và provider `hashicorp/aws ~> 5.0` để mọi người
   (và CI) dùng cùng phiên bản; commit `.terraform.lock.hcl`.
2. Định nghĩa biến `environment` có `validation`, biến `region` có mặc định.
3. Gom tag vào `locals`; tạo bucket bằng `for_each` trên tập vùng `raw`, `curated`.
4. Mỗi thuộc tính bảo mật/vận hành là một resource riêng, cũng `for_each = aws_s3_bucket.this`.
5. Xuất tên bucket ra `outputs.tf` để module khác (IAM, Glue, Airflow connection) dùng.
6. Mỗi môi trường chạy với tfvars và **state riêng**:

   ```bash
   terraform init -backend-config="key=olist/staging/terraform.tfstate"
   terraform plan -var="environment=staging" -out=plan.bin
   terraform apply plan.bin
   ```

## Quyết định thiết kế cần cân nhắc

| Quyết định | Lựa chọn | Đánh đổi |
| --- | --- | --- |
| Lặp bucket | `for_each` trên set vs khai báo 2 resource | `for_each` gọn, thêm vùng `sandbox` chỉ sửa một dòng; key là chuỗi nên đổi thứ tự không làm tạo lại (khác `count`) |
| Mã hoá | SSE-S3 (`AES256`) vs SSE-KMS | KMS có audit, phân quyền key, nhưng tốn phí theo request; bật `bucket_key_enabled` để giảm phí |
| Lifecycle | Chuyển `STANDARD_IA` sau 30 ngày cho raw | Raw ít đọc lại; curated đọc thường xuyên nên giữ STANDARD. IA tính phí tối thiểu 30 ngày và phí đọc |
| Phiên bản cũ | Xoá noncurrent sau 90 ngày | Versioning bảo vệ khỏi xoá nhầm nhưng làm phình chi phí nếu không dọn |
| Tách môi trường | Thư mục env gọi chung module / workspace / tfvars | Thư mục riêng an toàn nhất (state tách hẳn), workspace dễ nhầm |
| Tên bucket | `olist-<zone>-<env>` | Tên S3 là duy nhất toàn cầu; thực tế thêm account id hoặc hậu tố ngẫu nhiên |
| Prod | `prevent_destroy` trong `lifecycle {}` | Chặn `terraform destroy` lỡ tay xoá dữ liệu prod |
| Đóng gói | Đưa toàn bộ vào `modules/data_lake` | Tái sử dụng cho dự án khác, test module bằng `terraform test` |

Credential: không bao giờ đặt `access_key` trong provider. Local dùng `AWS_PROFILE`; CI dùng OIDC
(`aws-actions/configure-aws-credentials` với `role-to-assume`).

## Bản tham khảo

`main.tf`:

```hcl
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

locals {
  zones = toset(["raw", "curated"])
  tags = {
    project     = "olist"
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "aws_s3_bucket" "this" {
  for_each = local.zones
  bucket   = "olist-${each.key}-${var.environment}"
  tags     = merge(local.tags, { zone = each.key })
}

resource "aws_s3_bucket_versioning" "this" {
  for_each = aws_s3_bucket.this
  bucket   = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = aws_s3_bucket.this
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each                = aws_s3_bucket.this
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  for_each = aws_s3_bucket.this
  bucket   = each.value.id

  rule {
    id     = "tiering-and-cleanup"
    status = "Enabled"
    filter {}

    dynamic "transition" {
      for_each = each.key == "raw" ? [1] : []
      content {
        days          = 30
        storage_class = "STANDARD_IA"
      }
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
```

`variables.tf`:

```hcl
variable "environment" {
  type        = string
  description = "Môi trường triển khai"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment phải là dev, staging hoặc prod."
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}
```

`outputs.tf`:

```hcl
output "raw_bucket_name" {
  value = aws_s3_bucket.this["raw"].bucket
}

output "curated_bucket_name" {
  value = aws_s3_bucket.this["curated"].bucket
}
```

## Rubric (100 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Bộ test pass (cấu trúc đầy đủ), `terraform validate` thành công nếu chạy được | 30 |
| Bảo mật: encryption, 4 cờ public access block, không credential trong code | 20 |
| Tái sử dụng: `for_each`/module, không lặp code cho từng bucket | 15 |
| Quản lý môi trường: biến có validation, tên/tag theo môi trường, giải thích cách tách state | 15 |
| Chi phí và vòng đời dữ liệu: lifecycle hợp lý cho từng vùng, dọn phiên bản cũ | 10 |
| Trình bày: `terraform fmt`, mô tả biến, output hữu ích, README ngắn cách chạy | 10 |
