data "aws_caller_identity" "current" {}

# TODO 3: budget hằng tháng có cảnh báo ACTUAL (<= 80%) và FORECASTED (<= 100%) gửi var.alert_email.

locals {
  account       = data.aws_caller_identity.current.account_id
  function_name = "${var.prefix}-payments-worker"
  timeout       = 10
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.prefix}-payments-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "payments" {
  name                       = "${var.prefix}-payments"
  visibility_timeout_seconds = 6 * local.timeout
  message_retention_seconds  = 345600
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_dynamodb_table" "ledger" {
  name         = "${var.prefix}-seller-ledger"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "seller_id"

  attribute {
    name = "seller_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "idempotency" {
  name         = "${var.prefix}-payment-idempotency"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "payment_id"

  attribute {
    name = "payment_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account]
    }
  }
}

data "aws_iam_policy_document" "worker" {
  statement {
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.payments.arn]
  }
  statement {
    actions   = ["dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.ledger.arn]
  }
  statement {
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.idempotency.arn]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:us-east-1:${local.account}:log-group:/aws/lambda/${local.function_name}:*"]
  }
}

resource "aws_iam_role" "worker" {
  name               = local.function_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "worker" {
  name   = "payments-worker"
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker.json
}

# TODO 4: log group giữ log có hạn, Lambda arm64 và nhỏ, ESM giới hạn số Lambda đồng thời, alarm khi DLQ có message.
resource "aws_lambda_function" "worker" {
  function_name = local.function_name
  role          = aws_iam_role.worker.arn
  runtime       = "python3.12"
  handler       = "app.handler"
  filename      = var.package
  timeout       = local.timeout
  memory_size   = 1024

  environment {
    variables = {
      LEDGER_TABLE      = aws_dynamodb_table.ledger.name
      IDEMPOTENCY_TABLE = aws_dynamodb_table.idempotency.name
    }
  }
}

resource "aws_lambda_event_source_mapping" "payments" {
  event_source_arn        = aws_sqs_queue.payments.arn
  function_name           = aws_lambda_function.worker.arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
}

