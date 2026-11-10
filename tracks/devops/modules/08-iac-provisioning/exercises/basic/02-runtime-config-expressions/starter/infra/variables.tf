variable "prefix" {
  type = string
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "expected_account_id" {
  type    = string
  default = null
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
}

variable "retention" {
  type = list(object({
    prefix = string
    days   = number
  }))
  default = []
}

variable "db_password" {
  type = string
}
