locals {
  tags = {
    Project     = "olist-shop"
    Environment = var.environment
    ManagedBy   = "opentofu"
  }
  versioned = { for key, bucket in var.buckets : key => bucket if bucket.versioning }
  names     = { for key in keys(var.buckets) : key => "${var.prefix}-${var.environment}-${key}" }
  arns      = { for key, name in local.names : key => "arn:${data.aws_partition.current.partition}:s3:::${name}" }
}

data "aws_partition" "current" {}

resource "aws_s3_bucket" "this" {
  for_each = var.buckets

  bucket = local.names[each.key]
  tags   = local.tags
}

resource "aws_s3_bucket_versioning" "this" {
  for_each = local.versioned

  bucket = aws_s3_bucket.this[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each = var.buckets

  bucket                  = aws_s3_bucket.this[each.key].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "service" {
  for_each = var.services

  dynamic "statement" {
    for_each = length(each.value.read) > 0 ? [each.value.read] : []

    content {
      sid       = "ReadObjects"
      actions   = ["s3:GetObject"]
      resources = [for key in statement.value : "${local.arns[key]}/*"]
    }
  }

  dynamic "statement" {
    for_each = length(each.value.read) > 0 ? [each.value.read] : []

    content {
      sid       = "ListBuckets"
      actions   = ["s3:ListBucket"]
      resources = [for key in statement.value : local.arns[key]]
    }
  }

  dynamic "statement" {
    for_each = length(each.value.write) > 0 ? [each.value.write] : []

    content {
      sid       = "WriteObjects"
      actions   = ["s3:PutObject"]
      resources = [for key in statement.value : "${local.arns[key]}/*"]
    }
  }
}

resource "aws_iam_role" "service" {
  for_each = var.services

  name               = "${var.prefix}-${var.environment}-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy" "service" {
  for_each = { for key, service in var.services : key => service if length(concat(service.read, service.write)) > 0 }

  name   = "s3-access"
  role   = aws_iam_role.service[each.key].id
  policy = data.aws_iam_policy_document.service[each.key].json
}
