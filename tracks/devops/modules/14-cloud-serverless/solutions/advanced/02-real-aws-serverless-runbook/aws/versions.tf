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

  default_tags {
    tags = {
      Project   = "olist-serverless-lab"
      Owner     = var.owner
      ExpiresOn = var.expires_on
      ManagedBy = "opentofu"
    }
  }
}
