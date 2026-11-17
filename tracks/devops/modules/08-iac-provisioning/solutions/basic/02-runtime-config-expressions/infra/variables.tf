variable "prefix" {
  type = string
}

variable "environment" {
  type    = string
  default = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment chỉ nhận dev, staging hoặc prod."
  }
}

variable "expected_account_id" {
  type        = string
  default     = null
  description = "Tài khoản AWS mà cấu hình này được phép chạy; null thì không kiểm."
}

variable "services" {
  type = map(object({
    port     = number
    replicas = number
    public   = optional(bool, false)
    settings = optional(map(string), {})
  }))
  default = {
    api = {
      port     = 8000
      replicas = 1
      public   = true
    }
  }

  validation {
    condition     = alltrue([for service in values(var.services) : service.port >= 1024 && service.port <= 65535])
    error_message = "Cổng của service phải trong khoảng 1024-65535 (container không chạy root)."
  }
}

variable "retention" {
  type = list(object({
    prefix = string
    days   = number
  }))
  default = []
}

variable "db_password" {
  type      = string
  sensitive = true
  ephemeral = true

  validation {
    condition     = length(var.db_password) >= 16
    error_message = "db_password phải dài ít nhất 16 ký tự."
  }
}
