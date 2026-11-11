variable "prefix" {
  type = string
}

variable "function_timeout" {
  type    = number
  default = 10

  validation {
    condition     = var.function_timeout >= 3 && var.function_timeout <= 60
    error_message = "Timeout của worker trong khoảng 3..60 giây."
  }
}

variable "package" {
  type    = string
  default = "build/payments-worker.zip"
}
