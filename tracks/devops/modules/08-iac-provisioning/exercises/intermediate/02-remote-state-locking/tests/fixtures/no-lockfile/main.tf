terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.12.0"
    }
  }

  backend "s3" {
    bucket = "${var.prefix}-tfstate"
    key    = "olist/staging/platform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "prefix" {
  type = string
}

resource "aws_ssm_parameter" "carts_table" {
  name  = "/${var.prefix}/staging/carts/table"
  type  = "String"
  value = "${var.prefix}-staging-carts"
}
