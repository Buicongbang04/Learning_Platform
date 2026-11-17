moved {
  from = aws_s3_bucket.exports[0]
  to   = aws_s3_bucket.exports["orders"]
}

moved {
  from = aws_s3_bucket.exports[1]
  to   = aws_s3_bucket.exports["payments"]
}

moved {
  from = aws_s3_bucket.exports[2]
  to   = aws_s3_bucket.exports["reviews"]
}

moved {
  from = aws_s3_bucket_versioning.exports[0]
  to   = aws_s3_bucket_versioning.exports["orders"]
}

moved {
  from = aws_s3_bucket_versioning.exports[1]
  to   = aws_s3_bucket_versioning.exports["payments"]
}

moved {
  from = aws_s3_bucket_versioning.exports[2]
  to   = aws_s3_bucket_versioning.exports["reviews"]
}
