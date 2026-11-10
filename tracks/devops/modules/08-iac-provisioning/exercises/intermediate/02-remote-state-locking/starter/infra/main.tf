terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.12.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "prefix" {
  type = string
}

variable "environment" {
  type    = string
  default = "staging"
}

resource "aws_dynamodb_table" "carts" {
  name         = "${var.prefix}-${var.environment}-carts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cart_id"

  attribute {
    name = "cart_id"
    type = "S"
  }
}

resource "aws_ssm_parameter" "carts_table" {
  name  = "/${var.prefix}/${var.environment}/carts/table"
  type  = "String"
  value = aws_dynamodb_table.carts.name
}
