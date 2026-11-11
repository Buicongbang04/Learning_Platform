output "invoke_url" {
  value = "${aws_api_gateway_stage.lab.invoke_url}/payments"
}

output "queue_url" {
  value = aws_sqs_queue.payments.url
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}

output "function_name" {
  value = aws_lambda_function.worker.function_name
}
