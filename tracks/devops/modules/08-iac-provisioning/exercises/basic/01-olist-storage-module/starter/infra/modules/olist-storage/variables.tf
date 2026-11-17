variable "prefix" {
  type = string
}

variable "environment" {
  type = string
}

variable "buckets" {
  type = map(object({
    versioning = optional(bool, true)
  }))
}

variable "services" {
  type = map(object({
    read  = optional(list(string), [])
    write = optional(list(string), [])
  }))
}
