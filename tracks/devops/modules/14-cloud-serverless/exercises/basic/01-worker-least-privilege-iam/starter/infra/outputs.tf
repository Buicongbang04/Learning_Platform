output "role_name" {
  value = aws_iam_role.worker.name
}

output "role_arn" {
  value = aws_iam_role.worker.arn
}
