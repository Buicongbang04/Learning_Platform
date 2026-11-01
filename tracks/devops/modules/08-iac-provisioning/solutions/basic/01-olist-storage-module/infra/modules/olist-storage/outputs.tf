output "bucket_names" {
  description = "Khoá bucket -> tên bucket thật."
  value       = { for key, bucket in aws_s3_bucket.this : key => bucket.bucket }
}

output "bucket_arns" {
  description = "Khoá bucket -> ARN."
  value       = { for key, bucket in aws_s3_bucket.this : key => bucket.arn }
}

output "role_names" {
  description = "Service -> tên IAM role."
  value       = { for key, role in aws_iam_role.service : key => role.name }
}
