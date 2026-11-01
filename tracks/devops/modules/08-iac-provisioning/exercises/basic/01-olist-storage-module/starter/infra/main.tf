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

variable "environment" {
  type    = string
  default = "dev"
}

variable "buckets" {
  type = map(object({
    versioning = optional(bool, true)
  }))
  default = {
    media = {}
  }
}

variable "services" {
  type = map(object({
    read  = optional(list(string), [])
    write = optional(list(string), [])
  }))
  default = {}
}

module "storage" {
  source = "./modules/olist-storage"

  prefix      = var.prefix
  environment = var.environment
  buckets     = var.buckets
  services    = var.services
}

output "bucket_names" {
  value = module.storage.bucket_names
}

output "bucket_arns" {
  value = module.storage.bucket_arns
}

output "role_names" {
  value = module.storage.role_names
}
