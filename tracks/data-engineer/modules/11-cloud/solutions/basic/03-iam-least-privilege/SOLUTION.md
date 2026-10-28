# Lời giải: IAM policy least-privilege

## Cách làm

Bốn statement, mỗi cái một mục đích, đặt `Sid` có nghĩa để đọc log CloudTrail/Access Analyzer dễ:

| Sid | Effect | Action | Resource | Condition |
| --- | --- | --- | --- | --- |
| `ReadRawZone` | Allow | `s3:GetObject` | `arn:aws:s3:::olist-lake/raw/*` | |
| `WriteCuratedZoneWithKms` | Allow | `s3:PutObject` | `arn:aws:s3:::olist-lake/curated/*` | `StringEquals s3:x-amz-server-side-encryption = aws:kms` |
| `ListOnlyRawAndCurated` | Allow | `s3:ListBucket` | `arn:aws:s3:::olist-lake` | `StringLike s3:prefix in [raw/*, curated/*]` |
| `DenyInsecureTransport` | Deny | `s3:*` | `*` | `Bool aws:SecureTransport = false` |

## Vì sao

- **Object ARN vs bucket ARN**: `GetObject`/`PutObject` cần `bucket/key`, `ListBucket` cần ARN
  bucket. Viết `arn:aws:s3:::olist-lake/*` cho `ListBucket` thì list luôn bị từ chối.
- **Không có `DeleteObject`**: job ETL ghi đè theo partition (PutObject cùng key) là đủ; quyền xoá
  để cho job dọn dẹp riêng hoặc lifecycle rule. Bị lộ credential cũng không xoá được dữ liệu.
- **Condition KMS**: bắt buộc mã hoá ngay ở lớp quyền, không chỉ tin vào cấu hình bucket.
- **Explicit Deny thắng mọi Allow**: thứ tự đánh giá của IAM là explicit deny → allow → implicit
  deny. Vì thế statement Deny dùng wildcard rộng vẫn an toàn.
- `Resource "arn:aws:s3:::olist-lake*"` (thiếu `/`) là bẫy: khớp cả `olist-lake-backup`. Test có
  case này.

## Trong thực tế

- Policy SecureTransport thường đặt ở **bucket policy** (resource-based) để áp cho mọi principal,
  còn identity policy gắn vào role của job.
- Dùng **IAM Access Analyzer** (policy validation, unused access) và `aws iam simulate-principal-policy`
  để kiểm tra thay cho evaluator tự viết; Terraform có `data "aws_iam_policy_document"` để viết
  policy có kiểm tra cú pháp.
- Azure: role assignment với role `Storage Blob Data Reader` ở scope container; GCP:
  `roles/storage.objectViewer` gắn cho service account ở mức bucket, có IAM Conditions theo prefix
  (`resource.name.startsWith(...)`).
