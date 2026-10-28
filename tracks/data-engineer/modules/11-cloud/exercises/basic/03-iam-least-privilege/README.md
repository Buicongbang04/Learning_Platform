---
title: Viết IAM policy least-privilege cho job ETL
level: basic
services: []
files:
  - path: starter/policy.json
    note: 4 TODO (ghi trong khoá _TODO)
  - path: tests/test_iam_policy.py
    note: Không sửa. Có một evaluator IAM thu nhỏ
run:
  - uv run pytest tracks/data-engineer/modules/11-cloud/exercises/basic/03-iam-least-privilege -q
---

## Mục tiêu

Viết được một identity policy theo nguyên tắc **least privilege**: chỉ đúng action, đúng resource,
có condition, và hiểu cách IAM quyết định Allow/Deny (explicit deny thắng, mặc định là deny).

## Đề bài

Job ETL Olist chạy bằng role `olist-etl` trên bucket `olist-lake`. Starter `starter/policy.json`
đang cho `s3:*` trên `*` (rất hay gặp ngoài đời). Sửa thành policy chỉ cho phép:

1. **TODO 1** Đọc object ở vùng raw: `s3:GetObject` trên `arn:aws:s3:::olist-lake/raw/*`.
2. **TODO 2** Ghi object vào vùng curated: `s3:PutObject` trên `arn:aws:s3:::olist-lake/curated/*`,
   **chỉ khi** request có header mã hoá KMS: condition `StringEquals`
   `"s3:x-amz-server-side-encryption": "aws:kms"`.
3. **TODO 3** Liệt kê bucket nhưng chỉ trong hai prefix: `s3:ListBucket` trên
   `arn:aws:s3:::olist-lake` (ARN của bucket, không có `/*`) với condition `StringLike`
   `"s3:prefix": ["raw/*", "curated/*"]`.
4. **TODO 4** Một statement `Deny` mọi action `s3:*` trên mọi resource khi request không đi qua
   TLS: condition `Bool` `"aws:SecureTransport": "false"`.

Yêu cầu chung: `"Version": "2012-10-17"`, mỗi statement có `Sid` riêng, không statement `Allow` nào
dùng `"*"` hoặc `"s3:*"` làm action hay `"*"` làm resource. Xoá các khoá `_TODO` khi xong.

Test chứa một evaluator IAM thu nhỏ (hỗ trợ wildcard `*`/`?` trong Action/Resource, condition
`StringEquals`, `StringNotEquals`, `StringLike`, `Bool`; Deny thắng Allow; không khớp gì thì Deny)
và thử hàng loạt request hợp lệ lẫn không hợp lệ.

## Tiêu chí đạt

- JSON hợp lệ, `Version` đúng, mỗi statement có `Sid` duy nhất, không còn `_TODO`.
- Cho phép: đọc `raw/orders/...`, ghi `curated/...` kèm `aws:kms`, list với prefix `raw/` hoặc `curated/`.
- Từ chối: xoá object, ghi vào `raw/`, ghi `curated/` không có KMS, đọc bucket khác, list prefix
  `gold/` hoặc không có prefix, bất kỳ action IAM nào.
- Mọi request qua HTTP thường (`aws:SecureTransport = false`) đều bị từ chối, kể cả request hợp lệ.
- Không có wildcard rộng trong statement Allow.

## Gợi ý

### Gợi ý 1

`s3:ListBucket` áp lên **bucket** (`arn:aws:s3:::olist-lake`), còn `GetObject`/`PutObject` áp lên
**object** (`arn:aws:s3:::olist-lake/...`). Đặt nhầm ARN là lỗi phổ biến nhất khi viết policy S3.

### Gợi ý 2

```json
{
  "Sid": "DenyInsecureTransport",
  "Effect": "Deny",
  "Action": "s3:*",
  "Resource": "*",
  "Condition": {"Bool": {"aws:SecureTransport": "false"}}
}
```

Deny được phép dùng wildcard rộng: chặn rộng an toàn hơn cho phép rộng.
