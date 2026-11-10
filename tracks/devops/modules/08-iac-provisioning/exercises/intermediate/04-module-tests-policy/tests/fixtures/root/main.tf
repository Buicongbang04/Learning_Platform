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

module "reports" {
  source = "./modules/artifact-bucket"

  prefix = var.prefix
  name   = "reports"
}

module "uploads" {
  source = "./modules/upload-bucket"

  prefix = var.prefix
  name   = "uploads"
}

output "reports_bucket" {
  value = module.reports.bucket_name
}

output "reports_key" {
  value = module.reports.kms_key_arn
}

output "uploads_bucket" {
  value = module.uploads.bucket_name
}
