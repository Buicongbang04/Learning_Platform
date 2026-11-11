resource "aws_sqs_queue" "payments_dlq" {
  name                      = "${var.prefix}-payments-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "payments" {
  name                       = "${var.prefix}-payments"
  visibility_timeout_seconds = 6 * var.function_timeout
  message_retention_seconds  = 345600
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.payments_dlq.arn
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
