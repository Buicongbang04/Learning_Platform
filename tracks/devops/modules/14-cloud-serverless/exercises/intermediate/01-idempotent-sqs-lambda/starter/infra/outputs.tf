output "queue_url" {
  value = aws_sqs_queue.payments.url
}

output "dlq_url" {
  value = aws_sqs_queue.payments_dlq.url
}

output "ledger_table" {
  value = aws_dynamodb_table.ledger.name
}

output "idempotency_table" {
  value = aws_dynamodb_table.idempotency.name
}
