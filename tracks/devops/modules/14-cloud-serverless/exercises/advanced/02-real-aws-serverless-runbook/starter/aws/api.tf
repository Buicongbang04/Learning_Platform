data "aws_iam_policy_document" "apigw_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account]
    }
  }
}

data "aws_iam_policy_document" "apigw_send" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.payments.arn]
  }
}

resource "aws_iam_role" "apigw" {
  name               = "${var.prefix}-payments-api"
  assume_role_policy = data.aws_iam_policy_document.apigw_assume.json
}

resource "aws_iam_role_policy" "apigw" {
  name   = "send-payments"
  role   = aws_iam_role.apigw.id
  policy = data.aws_iam_policy_document.apigw_send.json
}

resource "aws_api_gateway_rest_api" "payments" {
  name = "${var.prefix}-payments"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "payments" {
  rest_api_id = aws_api_gateway_rest_api.payments.id
  parent_id   = aws_api_gateway_rest_api.payments.root_resource_id
  path_part   = "payments"
}

resource "aws_api_gateway_method" "post" {
  rest_api_id      = aws_api_gateway_rest_api.payments.id
  resource_id      = aws_api_gateway_resource.payments.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = false
}

resource "aws_api_gateway_integration" "sqs" {
  rest_api_id             = aws_api_gateway_rest_api.payments.id
  resource_id             = aws_api_gateway_resource.payments.id
  http_method             = aws_api_gateway_method.post.http_method
  type                    = "AWS"
  integration_http_method = "POST"
  uri                     = "arn:aws:apigateway:us-east-1:sqs:path/${local.account}/${aws_sqs_queue.payments.name}"
  credentials             = aws_iam_role.apigw.arn
  passthrough_behavior    = "NEVER"

  request_parameters = {
    "integration.request.header.Content-Type" = "'application/x-www-form-urlencoded'"
  }

  request_templates = {
    "application/json" = "Action=SendMessage&MessageBody=$util.urlEncode($input.body)"
  }
}

resource "aws_api_gateway_method_response" "accepted" {
  rest_api_id = aws_api_gateway_rest_api.payments.id
  resource_id = aws_api_gateway_resource.payments.id
  http_method = aws_api_gateway_method.post.http_method
  status_code = "202"
}

resource "aws_api_gateway_integration_response" "accepted" {
  rest_api_id = aws_api_gateway_rest_api.payments.id
  resource_id = aws_api_gateway_resource.payments.id
  http_method = aws_api_gateway_method.post.http_method
  status_code = aws_api_gateway_method_response.accepted.status_code

  response_templates = {
    "application/json" = "{\"accepted\": true}"
  }

  depends_on = [aws_api_gateway_integration.sqs]
}

resource "aws_api_gateway_deployment" "payments" {
  rest_api_id = aws_api_gateway_rest_api.payments.id

  triggers = {
    redeploy = sha1(jsonencode([aws_api_gateway_method.post, aws_api_gateway_integration.sqs, aws_api_gateway_integration_response.accepted]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "lab" {
  rest_api_id   = aws_api_gateway_rest_api.payments.id
  deployment_id = aws_api_gateway_deployment.payments.id
  stage_name    = "lab"
}

# TODO 5: chặn lạm dụng API: bắt API key, usage plan có quota theo ngày, throttling ở stage.
