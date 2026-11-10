terraform {
  backend "s3" {
    bucket       = "${var.prefix}-tfstate"
    key          = "olist/${var.environment}/platform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
