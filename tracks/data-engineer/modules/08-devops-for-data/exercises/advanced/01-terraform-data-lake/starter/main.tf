# TODO: khối terraform { required_version, required_providers { aws ... } }

provider "aws" {
  region = "us-east-1" # TODO: dùng var.region
}

# TODO: locals với tags chung (project, environment, managed_by)

# TODO: bucket raw và curated, tên phụ thuộc var.environment
resource "aws_s3_bucket" "raw" {
  bucket = "olist-raw"
}

# TODO: versioning, server-side encryption, public access block, lifecycle cho mỗi bucket
