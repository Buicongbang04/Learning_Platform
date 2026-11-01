variable "prefix" {
  type = string
}

variable "name" {
  type = string
}

module "bucket" {
  source = "../artifact-bucket"

  prefix          = var.prefix
  name            = var.name
  noncurrent_days = 14
}

output "bucket_name" {
  value = module.bucket.bucket_name
}
