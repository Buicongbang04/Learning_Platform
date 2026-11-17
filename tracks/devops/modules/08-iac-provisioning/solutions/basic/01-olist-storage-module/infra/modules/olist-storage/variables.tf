variable "prefix" {
  type        = string
  description = "Tiền tố chung cho mọi tên tài nguyên (mỗi lần chạy test một tiền tố riêng)."
}

variable "environment" {
  type        = string
  description = "Môi trường: dev, staging hoặc prod."

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment chỉ nhận dev, staging hoặc prod."
  }
}

variable "buckets" {
  type = map(object({
    versioning = optional(bool, true)
  }))
  description = "Bucket theo mục đích; khoá là tên ngắn (media, exports...)."

  validation {
    condition     = alltrue([for key in keys(var.buckets) : can(regex("^[a-z][a-z0-9-]{2,20}$", key))])
    error_message = "Khoá của buckets chỉ gồm chữ thường, số, gạch nối, bắt đầu bằng chữ, dài 3-21 ký tự."
  }
}

variable "services" {
  type = map(object({
    read  = optional(list(string), [])
    write = optional(list(string), [])
  }))
  description = "Service cần quyền S3: danh sách khoá bucket được đọc và được ghi."

  validation {
    condition = alltrue(flatten([
      for service in values(var.services) : [
        for key in concat(service.read, service.write) : contains(keys(var.buckets), key)
      ]
    ]))
    error_message = "services chỉ được tham chiếu bucket có trong buckets."
  }
}
