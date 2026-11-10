output "parameter_path" {
  description = "Đường dẫn SSM chứa cấu hình runtime; pipeline đọc cả cây bằng GetParametersByPath."
  value       = local.parameter_path
}

output "backup_bucket" {
  value = aws_s3_bucket.backups.bucket
}

output "kms_key_arn" {
  value = aws_kms_key.platform.arn
}

output "app_role_arn" {
  value = aws_iam_role.app.arn
}
