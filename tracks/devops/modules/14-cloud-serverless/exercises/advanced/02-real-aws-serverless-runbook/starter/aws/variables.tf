variable "prefix" {
  type = string
}

variable "owner" {
  type = string
}

# TODO 2: validation cho expires_on (YYYY-MM-DD) và monthly_budget_usd (0 < x <= 10).
variable "expires_on" {
  type = string
}

variable "alert_email" {
  type = string
}

variable "monthly_budget_usd" {
  type    = number
  default = 5
}

variable "package" {
  type    = string
  default = "build/payments-worker.zip"
}
