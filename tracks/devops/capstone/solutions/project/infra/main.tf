locals {
  name           = "${var.prefix}-${var.environment}"
  parameter_path = "/${var.prefix}/${var.environment}/olist-shop"
  tags = {
    Project     = "olist-shop"
    Environment = var.environment
    ManagedBy   = "opentofu"
  }
  parameters = {
    DB_HOST   = var.database_host
    DB_NAME   = "olist"
    DB_USER   = "olist"
    REDIS_URL = "redis://${var.redis_host}:6379/0"
    LOG_LEVEL = var.log_level
  }
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_partition" "current" {}

resource "aws_kms_key" "platform" {
  description             = "Olist Shop ${var.environment}: SSM SecureString và backup S3"
  enable_key_rotation     = true
  deletion_window_in_days = 7
}

resource "aws_kms_alias" "platform" {
  name          = "alias/${local.name}-olist-shop"
  target_key_id = aws_kms_key.platform.key_id
}

resource "aws_s3_bucket" "backups" {
  bucket = "${local.name}-backups"
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.platform.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "expire-noncurrent"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = var.backup_noncurrent_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }

  depends_on = [aws_s3_bucket_versioning.backups]
}

resource "aws_ssm_parameter" "plain" {
  for_each = local.parameters

  name  = "${local.parameter_path}/${each.key}"
  type  = "String"
  value = each.value
}

resource "aws_ssm_parameter" "db_password" {
  name             = "${local.parameter_path}/DB_PASSWORD"
  type             = "SecureString"
  key_id           = aws_kms_key.platform.arn
  value_wo         = var.db_password
  value_wo_version = var.db_password_version
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

locals {
  parameter_arn = "arn:${data.aws_partition.current.partition}:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${local.parameter_path}"
}

data "aws_iam_policy_document" "app" {
  statement {
    sid       = "ReadConfig"
    actions   = ["ssm:GetParameter", "ssm:GetParameters"]
    resources = ["${local.parameter_arn}/*"]
  }

  statement {
    sid       = "ReadConfigPath"
    actions   = ["ssm:GetParametersByPath"]
    resources = [local.parameter_arn]
  }

  statement {
    sid       = "DecryptConfig"
    actions   = ["kms:Decrypt"]
    resources = [aws_kms_key.platform.arn]
  }

  statement {
    sid       = "WriteBackups"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.backups.arn}/*"]
  }

  statement {
    sid       = "EncryptBackups"
    actions   = ["kms:GenerateDataKey"]
    resources = [aws_kms_key.platform.arn]
  }
}

resource "aws_iam_role" "app" {
  name               = "${local.name}-olist-app"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy" "app" {
  name   = "olist-app"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.app.json
}
