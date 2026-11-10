data "aws_caller_identity" "current" {}

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

# TODO 1: chỉ dịch vụ ECS task được assume role, và chỉ khi request đến từ chính tài khoản này (aws:SourceAccount).
data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com", "ec2.amazonaws.com"]
    }
  }
}

# TODO 2: thu hẹp về đúng hành động và đúng tài nguyên worker cần (xem bảng trong README).
data "aws_iam_policy_document" "worker" {
  statement {
    actions   = ["sqs:*", "s3:*", "secretsmanager:*"]
    resources = ["*"]
  }
}

# TODO 3: thêm managed policy "${var.prefix}-worker-boundary" làm permissions boundary cho role.
resource "aws_iam_role" "worker" {
  name               = "${var.prefix}-worker"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

resource "aws_iam_role_policy" "worker" {
  name   = "worker"
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker.json
}
