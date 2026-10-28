"""Thao tác data lake trên S3 bằng boto3: partition, multipart, lifecycle."""

from __future__ import annotations

from datetime import date

MiB = 1024 * 1024
MIN_PART_SIZE = 5 * MiB


def _check_name(label: str, value: str) -> None:
    if not value or "/" in value:
        raise ValueError(f"{label} không được rỗng hoặc chứa '/': {value!r}")


def partition_key(table: str, dt: date, filename: str, zone: str = "raw") -> str:
    _check_name("table", table)
    _check_name("filename", filename)
    return f"{zone}/{table}/year={dt:%Y}/month={dt:%m}/day={dt:%d}/{filename}"


def upload_partition(s3, bucket: str, table: str, dt: date, data: bytes,
                     filename: str = "part-0000.csv") -> str:
    key = partition_key(table, dt, filename)
    s3.put_object(Bucket=bucket, Key=key, Body=data)
    return key


def multipart_upload(s3, bucket: str, key: str, data: bytes, part_size: int = 8 * MiB) -> int:
    if part_size < MIN_PART_SIZE:
        raise ValueError(f"part_size tối thiểu {MIN_PART_SIZE} byte (5 MiB)")
    upload_id = s3.create_multipart_upload(Bucket=bucket, Key=key)["UploadId"]
    parts = []
    try:
        for number, offset in enumerate(range(0, len(data), part_size), start=1):
            response = s3.upload_part(Bucket=bucket, Key=key, UploadId=upload_id,
                                      PartNumber=number, Body=data[offset:offset + part_size])
            parts.append({"ETag": response["ETag"], "PartNumber": number})
        s3.complete_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id,
                                     MultipartUpload={"Parts": parts})
    except Exception:
        s3.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
        raise
    return len(parts)


def list_partitions(s3, bucket: str, table: str, zone: str = "raw", page_size: int = 1000) -> list[str]:
    prefix = f"{zone}/{table}/"
    found = set()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, PaginationConfig={"PageSize": page_size}):
        for obj in page.get("Contents", []):
            rest = obj["Key"][len(prefix):]
            if "/" in rest:
                found.add(rest.rsplit("/", 1)[0])
    return sorted(found)


def lifecycle_rules() -> dict:
    return {
        "Rules": [
            {
                "ID": "raw-tiering",
                "Status": "Enabled",
                "Filter": {"Prefix": "raw/"},
                "Transitions": [
                    {"Days": 30, "StorageClass": "STANDARD_IA"},
                    {"Days": 90, "StorageClass": "GLACIER"},
                ],
            },
            {
                "ID": "tmp-expire",
                "Status": "Enabled",
                "Filter": {"Prefix": "tmp/"},
                "Expiration": {"Days": 1},
            },
            {
                "ID": "abort-incomplete-mpu",
                "Status": "Enabled",
                "Filter": {"Prefix": ""},
                "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
            },
        ]
    }


def apply_lifecycle(s3, bucket: str) -> None:
    s3.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration=lifecycle_rules())
