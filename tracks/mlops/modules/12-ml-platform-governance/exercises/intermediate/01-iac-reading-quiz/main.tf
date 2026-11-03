terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

provider "aws" {
  region = "ap-southeast-1"
}

variable "lab_name" {
  type    = string
  default = "ml-lab"
}

locals {
  tags = {
    project = var.lab_name
    owner   = "learner"
    ttl     = "2026-12-01"
  }
}

resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.lab_name}-artifacts"
  tags   = local.tags
}

resource "aws_ecr_repository" "serving" {
  name = "${var.lab_name}/serving"
  tags = local.tags
}

resource "aws_iam_role" "sagemaker" {
  name = "${var.lab_name}-sagemaker"
  tags = local.tags
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "sagemaker.amazonaws.com" }
    }]
  })
}

resource "aws_sagemaker_notebook_instance" "dev" {
  name          = "${var.lab_name}-dev"
  role_arn      = aws_iam_role.sagemaker.arn
  instance_type = "ml.t3.medium"
  tags          = local.tags
}

resource "aws_sagemaker_model" "eta" {
  name               = "${var.lab_name}-eta"
  execution_role_arn = aws_iam_role.sagemaker.arn
  primary_container {
    image          = "${aws_ecr_repository.serving.repository_url}:v1"
    model_data_url = "s3://${aws_s3_bucket.artifacts.bucket}/eta/model.tar.gz"
  }
  tags = local.tags
}

resource "aws_sagemaker_endpoint_configuration" "eta" {
  name = "${var.lab_name}-eta"
  production_variants {
    variant_name           = "primary"
    model_name             = aws_sagemaker_model.eta.name
    instance_type          = "ml.m5.xlarge"
    initial_instance_count = 2
  }
  tags = local.tags
}

resource "aws_sagemaker_endpoint" "eta" {
  name                 = "${var.lab_name}-eta"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.eta.name
  tags                 = local.tags
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = local.tags
}

resource "aws_nat_gateway" "private" {
  allocation_id = aws_eip.nat.id
  subnet_id     = "subnet-0abc1234def567890"
  tags          = local.tags
}

resource "aws_budgets_budget" "lab" {
  name         = "${var.lab_name}-monthly"
  budget_type  = "COST"
  limit_amount = "20"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = ["learner@example.com"]
  }
}
