data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  account = data.aws_caller_identity.current.account_id
  region  = "us-east-1"
  arn     = data.aws_partition.current.partition
}

resource "aws_sqs_queue" "jobs" {
  name = "${var.prefix}-jobs"
}

resource "aws_s3_bucket" "reports" {
  bucket        = "${var.prefix}-reports"
  force_destroy = true
}

resource "aws_secretsmanager_secret" "db" {
  name                    = "${var.prefix}/olist/db"
  recovery_window_in_days = 0
}

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:${local.arn}:ecs:${local.region}:${local.account}:*"]
    }
  }
}

data "aws_iam_policy_document" "worker" {
  statement {
    sid       = "ConsumeJobs"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:ChangeMessageVisibility", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.jobs.arn]
  }
  statement {
    sid       = "WriteRevenueReports"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.reports.arn}/revenue/*"]
  }
  statement {
    sid       = "ReadDbSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.db.arn]
  }
}

data "aws_iam_policy_document" "boundary" {
  statement {
    sid       = "OnlyOwnQueues"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:ChangeMessageVisibility", "sqs:GetQueueAttributes", "sqs:SendMessage"]
    resources = ["arn:${local.arn}:sqs:${local.region}:${local.account}:${var.prefix}-*"]
  }
  statement {
    sid       = "OnlyOwnBuckets"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["arn:${local.arn}:s3:::${var.prefix}-*/*"]
  }
  statement {
    sid       = "OnlyOwnSecrets"
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = ["arn:${local.arn}:secretsmanager:${local.region}:${local.account}:secret:${var.prefix}/*"]
  }
}

resource "aws_iam_policy" "boundary" {
  name   = "${var.prefix}-worker-boundary"
  policy = data.aws_iam_policy_document.boundary.json
}

resource "aws_iam_role" "worker" {
  name                 = "${var.prefix}-worker"
  assume_role_policy   = data.aws_iam_policy_document.trust.json
  permissions_boundary = aws_iam_policy.boundary.arn
}

resource "aws_iam_role_policy" "worker" {
  name   = "worker"
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker.json
}
