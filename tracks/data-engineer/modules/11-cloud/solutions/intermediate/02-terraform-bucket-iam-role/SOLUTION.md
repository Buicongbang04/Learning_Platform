# Lời giải: bucket + IAM role cho Glue bằng Terraform

## Cách làm

1. `terraform {}` pin provider `~> 5.0`; biến `environment`, `region` có default.
2. Bucket `olist-lake-${var.environment}` + public access block 4 cờ (kế thừa module 08).
3. **Trust policy** (`assume_role_policy`): trả lời câu hỏi *ai được đội role này*. Ở đây chỉ
   service principal `glue.amazonaws.com`. Mỗi lần Glue job chạy, Glue gọi STS lấy **credential
   tạm thời** (hết hạn sau vài giờ) thay vì dùng access key cố định.
4. **Permission policy**: trả lời *đội role rồi được làm gì*. ARN dựng từ
   `aws_s3_bucket.lake.arn` nên đổi môi trường là đổi theo, và Terraform tự hiểu thứ tự tạo
   (bucket trước, policy sau).
5. Managed policy `AWSGlueServiceRole` cho quyền ghi CloudWatch Logs, đọc Glue Data Catalog.
   Lưu ý nó khá rộng (có `s3:GetObject` trên bucket tên `aws-glue-*`); ở môi trường nghiêm ngặt có
   thể thay bằng policy tự viết.

## Hai loại policy trên role

| | Trust policy | Permission policy |
| --- | --- | --- |
| Trả lời câu hỏi | Ai được assume role | Role được làm gì |
| Thuộc tính | `assume_role_policy` của `aws_iam_role` | `aws_iam_policy` + attachment, hoặc `aws_iam_role_policy` |
| Principal | Có (`Service`, `AWS`, `Federated`) | Không có (principal là chính role) |
| Lỗi hay gặp | `Principal = "*"`: ai cũng assume được | `s3:*` trên `*` |

## Chạy thử miễn phí với LocalStack

```bash
docker compose -f setup/docker-compose.yml up -d localstack
uv tool install terraform-local      # cung cấp lệnh tflocal, tự trỏ endpoint về localhost:4566
cd tracks/data-engineer/modules/11-cloud/solutions/intermediate/02-terraform-bucket-iam-role
tflocal init && tflocal apply -var environment=dev -auto-approve
aws --endpoint-url http://localhost:4566 iam get-role --role-name olist-glue-etl-dev
tflocal destroy -var environment=dev -auto-approve
```

Không dùng `tflocal` thì thêm vào provider:

```hcl
provider "aws" {
  region                      = var.region
  access_key                  = "test"   # chỉ cho LocalStack, KHÔNG commit cho cloud thật
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true
  endpoints {
    s3  = "http://localhost:4566"
    iam = "http://localhost:4566"
    sts = "http://localhost:4566"
  }
}
```

## Tương đương trên Azure và GCP

- **Azure**: *managed identity* (system-assigned cho Data Factory) + `azurerm_role_assignment`
  với role `Storage Blob Data Contributor` ở scope container `curated`, `Storage Blob Data Reader`
  ở scope container `raw`.
- **GCP**: `google_service_account` cho Dataflow worker + `google_storage_bucket_iam_member` với
  `roles/storage.objectViewer`/`objectCreator`; dùng Workload Identity (Federation) thay vì tải
  key JSON của service account.
