variable "prefix" {
  type = string
}

variable "name" {
  type = string
}

resource "aws_s3_bucket" "this" {
  bucket = "${var.prefix}-${var.name}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

output "bucket_name" {
  value = aws_s3_bucket.this.bucket
}
