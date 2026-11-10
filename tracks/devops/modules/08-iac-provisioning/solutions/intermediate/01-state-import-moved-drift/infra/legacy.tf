resource "aws_s3_bucket" "legacy_exports" {
  bucket = "${var.prefix}-legacy-exports"
  tags = {
    Project = "olist-shop"
    Owner   = "data-team"
  }
}

resource "aws_s3_bucket_versioning" "legacy_exports" {
  bucket = aws_s3_bucket.legacy_exports.id

  versioning_configuration {
    status = "Enabled"
  }
}
