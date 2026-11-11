resource "aws_sqs_queue" "payments_dlq" {
  name                      = "${var.prefix}-payments-dlq"
  message_retention_seconds = 1209600
}

# TODO 4: message lỗi mãi không được quay vòng tới hết hạn; sau vài lần nhận phải sang payments_dlq.
#         Message đang được worker xử lý không được hiện lại cho lần nhận khác.
resource "aws_sqs_queue" "payments" {
  name                      = "${var.prefix}-payments"
  message_retention_seconds = 345600
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

# TODO 5: bản ghi chống trùng tự hết hạn theo thuộc tính expires_at.
resource "aws_dynamodb_table" "idempotency" {
  name         = "${var.prefix}-payment-idempotency"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "payment_id"

  attribute {
    name = "payment_id"
    type = "S"
  }
}
