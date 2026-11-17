variable "prefix" {
  type        = string
  description = "Tiền tố chung của mọi tên tài nguyên."
}

variable "environment" {
  type        = string
  description = "Môi trường: staging hoặc prod."

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment chỉ nhận staging hoặc prod."
  }
}

variable "database_host" {
  type        = string
  description = "Endpoint Postgres (ở AWS thật là aws_db_instance.address)."
}

variable "redis_host" {
  type        = string
  description = "Endpoint Redis (ở AWS thật là endpoint của ElastiCache)."
}

variable "log_level" {
  type    = string
  default = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "log_level chỉ nhận DEBUG, INFO, WARNING, ERROR."
  }
}

variable "backup_noncurrent_days" {
  type    = number
  default = 30
}

variable "db_password" {
  type        = string
  sensitive   = true
  ephemeral   = true
  description = "Mật khẩu Postgres; chỉ đi qua thuộc tính write-only nên không bao giờ nằm trong state hay plan."
}

variable "db_password_version" {
  type        = number
  default     = 1
  description = "Tăng số này để ghi mật khẩu mới lên SSM (xoay mật khẩu)."
}

variable "state_passphrase" {
  type        = string
  sensitive   = true
  description = "Passphrase mã hoá state và plan (ít nhất 16 ký tự)."
}
