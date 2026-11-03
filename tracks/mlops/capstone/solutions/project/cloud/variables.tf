variable "region" {
  description = "Vùng AWS; us-east-1 có đủ dịch vụ free tier dùng ở đây"
  type        = string
  default     = "us-east-1"
}

variable "suffix" {
  description = "Hậu tố để tên bucket là duy nhất toàn cầu, ví dụ 4 ký tự hex ngẫu nhiên"
  type        = string
}

variable "owner" {
  description = "Người chịu trách nhiệm tài nguyên (ghi vào tag owner)"
  type        = string
}

variable "alert_email" {
  description = "Email nhận cảnh báo budget"
  type        = string
}

variable "budget_usd" {
  description = "Trần chi phí mỗi tháng của cả tài khoản, USD"
  type        = string
  default     = "1"
}

variable "model_path" {
  description = "Đường dẫn tệp model local sẽ đẩy lên S3 (models/model.joblib của M01)"
  type        = string
  default     = "../models/model.joblib"
}

variable "model_version" {
  description = "Version model trong registry (ghi vào key S3 và vào /healthz)"
  type        = string
  default     = "local"
}
