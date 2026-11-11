terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.12.0"
    }
  }
}

# TODO 1: default_tags Project = "olist-serverless-lab", Owner, ExpiresOn cho mọi tài nguyên.
provider "aws" {
  region = "us-east-1"

}
