terraform {
  backend "s3" {
    bucket       = "${var.prefix}-tfstate"
    key          = "olist-shop/${var.environment}/platform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }

  encryption {
    key_provider "pbkdf2" "state" {
      passphrase = var.state_passphrase
    }

    method "aes_gcm" "state" {
      keys = key_provider.pbkdf2.state
    }

    state {
      method   = method.aes_gcm.state
      enforced = true
    }

    plan {
      method   = method.aes_gcm.state
      enforced = true
    }
  }
}
