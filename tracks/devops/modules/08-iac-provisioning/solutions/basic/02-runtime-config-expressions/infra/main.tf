locals {
  base_path = "/${var.prefix}/${var.environment}"
  settings = merge([
    for service, config in var.services : {
      for key, value in config.settings : "${local.base_path}/${service}/${key}" => value
    }
  ]...)
  public_services = { for name, config in var.services : name => config if config.public }
}

data "aws_caller_identity" "current" {
  lifecycle {
    postcondition {
      condition     = var.expected_account_id == null || self.account_id == var.expected_account_id
      error_message = "Đang chạy trên tài khoản ${self.account_id}, khác expected_account_id."
    }
  }
}

resource "aws_ssm_parameter" "setting" {
  for_each = local.settings

  name  = each.key
  type  = "String"
  value = each.value
}

resource "aws_ssm_parameter" "db_password" {
  name             = "${local.base_path}/db/password"
  type             = "SecureString"
  value_wo         = var.db_password
  value_wo_version = 1
}

resource "aws_s3_bucket" "config" {
  bucket = "${var.prefix}-${var.environment}-runtime-config"
}

resource "aws_s3_bucket_lifecycle_configuration" "config" {
  bucket = aws_s3_bucket.config.id

  dynamic "rule" {
    for_each = var.retention

    content {
      id     = "expire-${trimsuffix(rule.value.prefix, "/")}"
      status = "Enabled"

      filter {
        prefix = rule.value.prefix
      }

      expiration {
        days = rule.value.days
      }
    }
  }
}

resource "aws_s3_object" "upstreams" {
  bucket       = aws_s3_bucket.config.id
  key          = "nginx/upstreams.conf"
  content_type = "text/plain"
  content      = templatefile("${path.module}/templates/upstreams.conf.tftpl", { services = local.public_services })

  lifecycle {
    precondition {
      condition     = length(local.public_services) > 0
      error_message = "Cần ít nhất một service public để sinh upstream cho Nginx."
    }
  }
}

check "prod_redundancy" {
  assert {
    condition     = var.environment != "prod" || alltrue([for service in values(var.services) : service.replicas >= 2])
    error_message = "Ở prod mọi service nên có ít nhất 2 replica."
  }
}
