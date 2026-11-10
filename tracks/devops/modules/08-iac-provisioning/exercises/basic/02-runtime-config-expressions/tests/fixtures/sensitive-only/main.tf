terraform {
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

variable "db_password" {
  type      = string
  sensitive = true
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.prefix}/staging/db/password"
  type  = "SecureString"
  value = var.db_password
}
