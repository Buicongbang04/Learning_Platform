# Bucket data lake + IAM role cho job AWS Glue (least privilege, không access key tĩnh).

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "environment" {
  type        = string
  description = "dev, staging hoặc prod"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

locals {
  tags = {
    project     = "olist"
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "aws_s3_bucket" "lake" {
  bucket = "olist-lake-${var.environment}"
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Trust policy: chỉ dịch vụ Glue được assume role này.
resource "aws_iam_role" "glue_etl" {
  name = "olist-glue-etl-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "GlueAssumeRole"
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

# Permission policy: đọc raw, ghi curated, liệt kê bucket.
resource "aws_iam_policy" "glue_etl_s3" {
  name = "olist-glue-etl-s3-${var.environment}"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadRaw"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["${aws_s3_bucket.lake.arn}/raw/*"]
      },
      {
        Sid      = "WriteCurated"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = ["${aws_s3_bucket.lake.arn}/curated/*"]
      },
      {
        Sid      = "ListLake"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = [aws_s3_bucket.lake.arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_etl_s3" {
  role       = aws_iam_role.glue_etl.name
  policy_arn = aws_iam_policy.glue_etl_s3.arn
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_etl.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

output "glue_role_arn" {
  value = aws_iam_role.glue_etl.arn
}

output "lake_bucket" {
  value = aws_s3_bucket.lake.bucket
}
