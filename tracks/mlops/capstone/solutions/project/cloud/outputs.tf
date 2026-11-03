output "health_url" {
  description = "URL của endpoint /healthz trên Lambda"
  value       = aws_lambda_function_url.health.function_url
}

output "model_uri" {
  description = "Vị trí model trên S3"
  value       = "s3://${aws_s3_bucket.models.id}/${local.model_key}"
}
