data "aws_caller_identity" "current" {}

locals {
  function_name = "${var.prefix}-payments-worker"
  log_group_arn = "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.function_name}"
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

data "aws_iam_policy_document" "worker" {
  statement {
    sid       = "ConsumePayments"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.payments.arn]
  }
  statement {
    sid       = "CreditLedger"
    actions   = ["dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.ledger.arn]
  }
  statement {
    sid       = "RecordPayment"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.idempotency.arn]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${local.log_group_arn}:*"]
  }
}

resource "aws_iam_role" "worker" {
  name               = local.function_name
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy" "worker" {
  name   = "payments-worker"
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker.json
}

resource "aws_lambda_function" "worker" {
  function_name = local.function_name
  role          = aws_iam_role.worker.arn
  runtime       = "python3.12"
  handler       = "app.handler"
  filename      = var.package
  timeout       = var.function_timeout
  memory_size   = 256

  environment {
    variables = {
      LEDGER_TABLE      = aws_dynamodb_table.ledger.name
      IDEMPOTENCY_TABLE = aws_dynamodb_table.idempotency.name
    }
  }
}

resource "aws_lambda_event_source_mapping" "payments" {
  event_source_arn                   = aws_sqs_queue.payments.arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 1
  function_response_types            = ["ReportBatchItemFailures"]

  scaling_config {
    maximum_concurrency = 5
  }
}
