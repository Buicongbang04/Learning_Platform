output "parameter_names" {
  value = sort(values(aws_ssm_parameter.setting)[*].name)
}

output "public_services" {
  value = sort(keys(local.public_services))
}

output "db_password_parameter" {
  value = aws_ssm_parameter.db_password.name
}

output "account_id" {
  value = data.aws_caller_identity.current.account_id
}
