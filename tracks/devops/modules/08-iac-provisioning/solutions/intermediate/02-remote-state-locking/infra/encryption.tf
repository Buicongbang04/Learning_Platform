variable "state_passphrase" {
  type        = string
  sensitive   = true
  description = "Passphrase mã hoá state và plan (pbkdf2 đòi ít nhất 16 ký tự); CI đọc từ secret store, không ghi vào tfvars."
}

terraform {
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
