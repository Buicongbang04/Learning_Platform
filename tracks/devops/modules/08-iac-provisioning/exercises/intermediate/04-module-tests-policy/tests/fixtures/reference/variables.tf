variable "prefix" {
  type        = string
  description = "Tiền tố chung của mọi tên tài nguyên."
}

variable "name" {
  type        = string
  description = "Tên ngắn của bucket (reports, builds...)."

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.name))
    error_message = "name chỉ gồm chữ thường, số, gạch nối, bắt đầu bằng chữ, dài 3-31 ký tự."
  }
}

variable "noncurrent_days" {
  type        = number
  default     = 30
  description = "Số ngày giữ phiên bản cũ của object trước khi xoá."

  validation {
    condition     = var.noncurrent_days >= 1 && var.noncurrent_days <= 365
    error_message = "noncurrent_days phải trong khoảng 1-365."
  }
}
