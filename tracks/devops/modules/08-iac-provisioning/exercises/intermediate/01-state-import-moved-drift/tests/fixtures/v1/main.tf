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

resource "aws_s3_bucket" "invoices" {
  bucket = "${var.prefix}-invoices"
  tags = {
    Project = "olist-shop"
  }
}

resource "aws_s3_bucket_versioning" "invoices" {
  bucket = aws_s3_bucket.invoices.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "reports" {
  bucket = "${var.prefix}-reports"
  tags = {
    Project = "olist-shop"
  }
}

resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "scratch" {
  bucket = "${var.prefix}-scratch"
}
