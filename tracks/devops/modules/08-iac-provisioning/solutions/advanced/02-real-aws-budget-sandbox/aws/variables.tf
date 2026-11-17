variable "prefix" {
  type        = string
  description = "Tiền tố mọi tên tài nguyên, ví dụ olist-sandbox-<tên bạn>."
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "owner" {
  type        = string
  description = "Người chịu trách nhiệm (email hay username)."
}

variable "expires_on" {
  type        = string
  description = "Ngày phải destroy, dạng YYYY-MM-DD."

  validation {
    condition     = can(regex("^\\d{4}-\\d{2}-\\d{2}$", var.expires_on))
    error_message = "expires_on phải có dạng YYYY-MM-DD."
  }
}

variable "alert_email" {
  type        = string
  description = "Email nhận cảnh báo budget."

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email phải là địa chỉ email."
  }
}

variable "monthly_budget_usd" {
  type    = number
  default = 5

  validation {
    condition     = var.monthly_budget_usd > 0 && var.monthly_budget_usd <= 10
    error_message = "Budget của sandbox tối đa 10 USD mỗi tháng."
  }
}

variable "instance_type" {
  type    = string
  default = "t4g.nano"

  validation {
    condition     = contains(["t4g.nano", "t4g.micro"], var.instance_type)
    error_message = "Sandbox chỉ dùng t4g.nano hoặc t4g.micro."
  }
}

variable "ami_id" {
  type        = string
  description = "AMI Amazon Linux 2023 arm64 của region (lấy từ SSM public parameter)."

  validation {
    condition     = can(regex("^ami-[0-9a-f]{8,17}$", var.ami_id))
    error_message = "ami_id phải có dạng ami-xxxxxxxx."
  }
}
