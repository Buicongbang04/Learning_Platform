variable "prefix" {
  type = string
}

variable "names" {
  type = set(string)
}

resource "aws_s3_bucket" "this" {
  for_each = var.names

  bucket = "${var.prefix}-${each.key}"
  tags = {
    Project = "olist-shop"
  }
}

resource "aws_s3_bucket_versioning" "this" {
  for_each = var.names

  bucket = aws_s3_bucket.this[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}

output "bucket_names" {
  value = { for key, bucket in aws_s3_bucket.this : key => bucket.bucket }
}
