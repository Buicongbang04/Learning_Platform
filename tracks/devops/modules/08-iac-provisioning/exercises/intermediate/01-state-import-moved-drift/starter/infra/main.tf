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

module "documents" {
  source = "./modules/documents"

  prefix = var.prefix
  names  = ["invoices", "reports"]
}

output "document_buckets" {
  value = module.documents.bucket_names
}
