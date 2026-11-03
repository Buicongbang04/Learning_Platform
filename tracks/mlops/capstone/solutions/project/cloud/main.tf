locals {
  prefix = "eta-mlops"
  tags = {
    project    = "eta-mlops"
    owner      = var.owner
    milestone  = "m11"
    managed_by = "terraform"
  }
  model_key = "models/eta/${var.model_version}/model.joblib"
}

resource "aws_s3_bucket" "models" {
  bucket        = "${local.prefix}-models-${var.suffix}"
  force_destroy = true
  tags          = local.tags
}

resource "aws_s3_bucket_public_access_block" "models" {
  bucket                  = aws_s3_bucket.models.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_object" "model" {
  bucket = aws_s3_bucket.models.id
  key    = local.model_key
  source = var.model_path
  etag   = filemd5(var.model_path)
  tags   = local.tags
}

resource "aws_iam_role" "health" {
  name = "${local.prefix}-health-role"
  path = "/eta-mlops/"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "health" {
  name = "${local.prefix}-health"
  role = aws_iam_role.health.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.models.arn}/models/*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.health.arn}:*"
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "health" {
  name              = "/aws/lambda/${local.prefix}-health"
  retention_in_days = 3
  tags              = local.tags
}

data "archive_file" "health" {
  type        = "zip"
  source_file = "${path.module}/lambda/health.py"
  output_path = "${path.module}/build/health.zip"
}

resource "aws_lambda_function" "health" {
  function_name    = "${local.prefix}-health"
  role             = aws_iam_role.health.arn
  runtime          = "python3.12"
  handler          = "health.handler"
  filename         = data.archive_file.health.output_path
  source_code_hash = data.archive_file.health.output_base64sha256
  memory_size      = 128
  timeout          = 5
  environment {
    variables = {
      MODEL_BUCKET  = aws_s3_bucket.models.id
      MODEL_KEY     = local.model_key
      MODEL_VERSION = var.model_version
    }
  }
  depends_on = [aws_cloudwatch_log_group.health]
  tags       = local.tags
}

resource "aws_lambda_function_url" "health" {
  function_name      = aws_lambda_function.health.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "health_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.health.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "health_invoke" {
  statement_id             = "AllowPublicInvokeViaUrl"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.health.function_name
  principal                = "*"
  invoked_via_function_url = true
}

resource "aws_budgets_budget" "monthly" {
  name         = "${local.prefix}-monthly"
  budget_type  = "COST"
  limit_amount = var.budget_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }

  tags = local.tags
}
