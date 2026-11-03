"""Endpoint nhỏ trên Lambda: báo model nào đang nằm trên S3, không nạp model (giữ trong free tier, không cần sklearn)."""

import json
import os

import boto3


def handler(event, context):
    bucket, key = os.environ["MODEL_BUCKET"], os.environ["MODEL_KEY"]
    head = boto3.client("s3").head_object(Bucket=bucket, Key=key)
    body = {
        "status": "ok",
        "model_version": os.environ.get("MODEL_VERSION", "unknown"),
        "artifact": f"s3://{bucket}/{key}",
        "bytes": head["ContentLength"],
        "etag": head["ETag"].strip('"'),
    }
    return {"statusCode": 200, "headers": {"content-type": "application/json"}, "body": json.dumps(body)}
