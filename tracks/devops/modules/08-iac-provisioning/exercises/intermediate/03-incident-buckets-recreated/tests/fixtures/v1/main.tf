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

variable "export_names" {
  type    = list(string)
  default = ["orders", "payments", "reviews"]
}

resource "aws_s3_bucket" "exports" {
  count = length(var.export_names)

  bucket = "${var.prefix}-exports-${var.export_names[count.index]}"
  tags = {
    Project = "olist-shop"
    Dataset = var.export_names[count.index]
  }
}

resource "aws_s3_bucket_versioning" "exports" {
  count = length(var.export_names)

  bucket = aws_s3_bucket.exports[count.index].id

  versioning_configuration {
    status = "Enabled"
  }
}
