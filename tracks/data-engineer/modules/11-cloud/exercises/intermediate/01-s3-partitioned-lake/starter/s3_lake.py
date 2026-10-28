"""Thao tác data lake trên S3 bằng boto3: partition, multipart, lifecycle."""

from __future__ import annotations

from datetime import date

MiB = 1024 * 1024
MIN_PART_SIZE = 5 * MiB


def partition_key(table: str, dt: date, filename: str, zone: str = "raw") -> str:
    # TODO 1: "<zone>/<table>/year=YYYY/month=MM/day=DD/<filename>"; rỗng hoặc có "/" -> ValueError
    raise NotImplementedError


def upload_partition(s3, bucket: str, table: str, dt: date, data: bytes,
                     filename: str = "part-0000.csv") -> str:
    # TODO 2: put_object vào partition_key(...), trả về key
    raise NotImplementedError


def multipart_upload(s3, bucket: str, key: str, data: bytes, part_size: int = 8 * MiB) -> int:
    # TODO 3: kiểm tra part_size >= MIN_PART_SIZE; create -> upload_part -> complete;
    #         lỗi giữa chừng -> abort_multipart_upload rồi raise lại. Trả về số part.
    raise NotImplementedError


def list_partitions(s3, bucket: str, table: str, zone: str = "raw", page_size: int = 1000) -> list[str]:
    # TODO 4: paginator list_objects_v2 với PaginationConfig={"PageSize": page_size};
    #         trả list partition duy nhất, đã sắp xếp, dạng "year=2018/month=01/day=05"
    raise NotImplementedError


def lifecycle_rules() -> dict:
    # TODO 5: {"Rules": [raw-tiering, tmp-expire, abort-incomplete-mpu]}
    raise NotImplementedError


def apply_lifecycle(s3, bucket: str) -> None:
    # TODO 6: put_bucket_lifecycle_configuration với lifecycle_rules()
    raise NotImplementedError
