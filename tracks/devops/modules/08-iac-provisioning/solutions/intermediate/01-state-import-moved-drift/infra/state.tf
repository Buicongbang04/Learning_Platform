moved {
  from = aws_s3_bucket.invoices
  to   = module.documents.aws_s3_bucket.this["invoices"]
}

moved {
  from = aws_s3_bucket.reports
  to   = module.documents.aws_s3_bucket.this["reports"]
}

moved {
  from = aws_s3_bucket_versioning.invoices
  to   = module.documents.aws_s3_bucket_versioning.this["invoices"]
}

moved {
  from = aws_s3_bucket_versioning.reports
  to   = module.documents.aws_s3_bucket_versioning.this["reports"]
}

import {
  to = aws_s3_bucket.legacy_exports
  id = "${var.prefix}-legacy-exports"
}

import {
  to = aws_s3_bucket_versioning.legacy_exports
  id = "${var.prefix}-legacy-exports"
}

removed {
  from = aws_s3_bucket.scratch

  lifecycle {
    destroy = false
  }
}
