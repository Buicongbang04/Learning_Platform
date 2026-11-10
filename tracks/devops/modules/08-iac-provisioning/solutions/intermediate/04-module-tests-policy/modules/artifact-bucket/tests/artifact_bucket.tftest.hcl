mock_provider "aws" {
  mock_resource "aws_kms_key" {
    defaults = {
      arn = "arn:aws:kms:us-east-1:000000000000:key/mock-key"
    }
  }

  mock_resource "aws_s3_bucket" {
    defaults = {
      arn = "arn:aws:s3:::devops-ex-test0000-reports"
    }
  }
}

variables {
  prefix = "devops-ex-test0000"
  name   = "reports"
}

run "names_follow_prefix" {
  command = plan

  assert {
    condition     = aws_s3_bucket.this.bucket == "devops-ex-test0000-reports"
    error_message = "Tên bucket phải là <prefix>-<name>."
  }

  assert {
    condition     = aws_kms_alias.this.name == "alias/devops-ex-test0000-reports"
    error_message = "Alias KMS phải là alias/<prefix>-<name>."
  }
}

run "versioning_enabled" {
  command = plan

  assert {
    condition     = aws_s3_bucket_versioning.this.versioning_configuration[0].status == "Enabled"
    error_message = "Versioning phải Enabled."
  }
}

run "public_access_fully_blocked" {
  command = plan

  assert {
    condition = alltrue([
      aws_s3_bucket_public_access_block.this.block_public_acls,
      aws_s3_bucket_public_access_block.this.block_public_policy,
      aws_s3_bucket_public_access_block.this.ignore_public_acls,
      aws_s3_bucket_public_access_block.this.restrict_public_buckets,
    ])
    error_message = "Phải bật đủ 4 cờ public access block."
  }
}

run "kms_key_rotates" {
  command = plan

  assert {
    condition     = aws_kms_key.this.enable_key_rotation
    error_message = "Khoá KMS phải bật xoay khoá."
  }
}

run "encrypted_with_module_key" {
  assert {
    condition = alltrue([
      for rule in aws_s3_bucket_server_side_encryption_configuration.this.rule :
      alltrue([
        for item in rule.apply_server_side_encryption_by_default :
        item.sse_algorithm == "aws:kms" && item.kms_master_key_id == aws_kms_key.this.arn
      ])
    ])
    error_message = "Bucket phải mã hoá aws:kms bằng đúng khoá của module."
  }

  assert {
    condition     = output.kms_key_arn == "arn:aws:kms:us-east-1:000000000000:key/mock-key"
    error_message = "Output kms_key_arn phải trỏ khoá của module."
  }
}

run "rejects_zero_retention" {
  command = plan

  variables {
    noncurrent_days = 0
  }

  expect_failures = [var.noncurrent_days]
}

run "rejects_too_long_retention" {
  command = plan

  variables {
    noncurrent_days = 400
  }

  expect_failures = [var.noncurrent_days]
}
