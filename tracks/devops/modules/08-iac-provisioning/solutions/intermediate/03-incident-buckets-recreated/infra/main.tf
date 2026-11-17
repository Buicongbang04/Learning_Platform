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

variable "export_names" {
  type    = set(string)
  default = ["orders", "payments", "reviews"]
}

resource "aws_s3_bucket" "exports" {
  for_each = var.export_names

  bucket = "${var.prefix}-exports-${each.key}"
  tags = {
    Project = "olist-shop"
    Dataset = each.key
  }
}

resource "aws_s3_bucket_versioning" "exports" {
  for_each = var.export_names

  bucket = aws_s3_bucket.exports[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}
