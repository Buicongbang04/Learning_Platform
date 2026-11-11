variable "prefix" {
  type = string
}

variable "owner" {
  type = string
}

variable "expires_on" {
  type = string

  validation {
    condition     = can(regex("^\\d{4}-\\d{2}-\\d{2}$", var.expires_on))
    error_message = "expires_on dạng YYYY-MM-DD."
  }
}

variable "alert_email" {
  type = string
}

variable "monthly_budget_usd" {
  type    = number
  default = 5

  validation {
    condition     = var.monthly_budget_usd > 0 && var.monthly_budget_usd <= 10
    error_message = "Budget của lab trong khoảng (0, 10] USD."
  }
}

variable "package" {
  type    = string
  default = "build/payments-worker.zip"
}
