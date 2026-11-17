variable "prefix" {
  type = string
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "owner" {
  type = string
}

variable "expires_on" {
  type = string
}

variable "alert_email" {
  type = string
}

variable "ami_id" {
  type = string
}
