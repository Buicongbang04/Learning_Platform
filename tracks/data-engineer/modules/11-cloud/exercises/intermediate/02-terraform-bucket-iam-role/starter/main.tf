# Bucket data lake + IAM role cho job AWS Glue (least privilege, không access key tĩnh).

# TODO 1: khối terraform { required_version, required_providers { aws = { source, version } } }
#         provider "aws" { region = var.region }
#         variable "environment" và variable "region" (có default)

# TODO 2: aws_s3_bucket "lake" tên "olist-lake-${var.environment}"
#         + aws_s3_bucket_public_access_block đủ 4 cờ true

# TODO 3: aws_iam_role "glue_etl" với assume_role_policy cho service glue.amazonaws.com

# TODO 4: aws_iam_policy (GetObject raw/*, PutObject curated/*, ListBucket bucket)
#         + aws_iam_role_policy_attachment gắn vào role

# TODO 5: attachment managed policy AWSGlueServiceRole + output ARN của role
