"""Mặc định chạy offline bằng moto. S3_BACKEND=localstack (hoặc minio) để chạy trên dịch vụ Docker thật."""

import importlib.util
import os
import uuid
from datetime import date

import pytest

import testkit
from testkit import Exercise

ex = Exercise(__file__)
MiB = 1024 * 1024


def m():
    return ex.module("s3_lake.py")


# ---------- hàm thuần, không cần S3 ----------

def test_partition_key():
    key = m().partition_key("orders", date(2018, 1, 5), "part-0000.csv")
    assert key == "raw/orders/year=2018/month=01/day=05/part-0000.csv"
    key = m().partition_key("payments", date(2017, 12, 31), "a.parquet", zone="curated")
    assert key == "curated/payments/year=2017/month=12/day=31/a.parquet"


@pytest.mark.parametrize("table, filename", [("", "a.csv"), ("orders", ""), ("a/b", "x.csv"), ("orders", "x/y.csv")])
def test_partition_key_rejects_bad_names(table, filename):
    with pytest.raises(ValueError):
        m().partition_key(table, date(2018, 1, 1), filename)


def test_lifecycle_rules_shape():
    rules = {r["ID"]: r for r in m().lifecycle_rules()["Rules"]}
    assert set(rules) == {"raw-tiering", "tmp-expire", "abort-incomplete-mpu"}
    assert all(r["Status"] == "Enabled" for r in rules.values())
    raw = rules["raw-tiering"]
    assert raw["Filter"] == {"Prefix": "raw/"}
    transitions = sorted((t["Days"], t["StorageClass"]) for t in raw["Transitions"])
    assert transitions == [(30, "STANDARD_IA"), (90, "GLACIER")]
    assert rules["tmp-expire"]["Filter"] == {"Prefix": "tmp/"}
    assert rules["tmp-expire"]["Expiration"] == {"Days": 1}
    assert rules["abort-incomplete-mpu"]["AbortIncompleteMultipartUpload"] == {"DaysAfterInitiation": 7}


def test_multipart_rejects_small_parts():
    with pytest.raises(ValueError):
        m().multipart_upload(None, "b", "k", b"x" * 10, part_size=1 * MiB)


class FailingS3:
    """S3 giả: upload_part lần 2 lỗi, ghi lại các lời gọi."""

    def __init__(self):
        self.calls = []
        self.parts = 0

    def create_multipart_upload(self, **kw):
        self.calls.append(("create", kw))
        return {"UploadId": "upload-123"}

    def upload_part(self, **kw):
        self.parts += 1
        self.calls.append(("upload_part", kw["PartNumber"]))
        if self.parts == 2:
            raise ConnectionError("mạng chập chờn")
        return {"ETag": f'"etag-{self.parts}"'}

    def complete_multipart_upload(self, **kw):
        self.calls.append(("complete", kw))
        return {}

    def abort_multipart_upload(self, **kw):
        self.calls.append(("abort", kw))
        return {}


def test_multipart_aborts_on_error():
    fake = FailingS3()
    with pytest.raises(ConnectionError):
        m().multipart_upload(fake, "lake", "raw/big.bin", b"x" * (12 * MiB), part_size=5 * MiB)
    names = [c[0] for c in fake.calls]
    assert "complete" not in names
    aborts = [c[1] for c in fake.calls if c[0] == "abort"]
    assert aborts and aborts[0]["UploadId"] == "upload-123" and aborts[0]["Key"] == "raw/big.bin"


# ---------- cần một S3 (moto / LocalStack / MinIO) ----------

@pytest.fixture
def s3(monkeypatch):
    boto3 = pytest.importorskip("boto3")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    backend = os.environ.get("S3_BACKEND", "moto")
    if backend == "moto" and importlib.util.find_spec("moto"):
        from moto import mock_aws

        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.backend = "moto"
            yield client
        return
    if backend in ("moto", "localstack") and testkit.service_up("localstack"):
        client = boto3.client("s3", endpoint_url=testkit.LOCALSTACK_ENDPOINT, region_name="us-east-1")
        client.backend = "localstack"
    elif backend in ("moto", "minio") and testkit.service_up("minio"):
        user, password = testkit.MINIO_AUTH
        client = boto3.client("s3", endpoint_url=testkit.MINIO_ENDPOINT, region_name="us-east-1",
                              aws_access_key_id=user, aws_secret_access_key=password)
        client.backend = "minio"
    else:
        pytest.skip(f"Không có S3 cho S3_BACKEND={backend}: bật bằng docker compose -f setup/docker-compose.yml up -d {backend}")
    yield client


@pytest.fixture
def bucket(s3):
    name = f"olist-lake-{uuid.uuid4().hex[:12]}"
    s3.create_bucket(Bucket=name)
    yield name
    if s3.backend != "moto":  # dọn bucket trên LocalStack/MinIO
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=name):
            for obj in page.get("Contents", []):
                s3.delete_object(Bucket=name, Key=obj["Key"])
        s3.delete_bucket(Bucket=name)


def test_upload_and_list_partitions(s3, bucket):
    lake = m()
    days = [date(2018, 1, 5), date(2018, 1, 6), date(2017, 12, 31), date(2018, 2, 1), date(2018, 1, 5)]
    for i, d in enumerate(days):
        key = lake.upload_partition(s3, bucket, "orders", d, f"order_id\n{i}\n".encode(), filename=f"part-{i:04d}.csv")
        assert key == lake.partition_key("orders", d, f"part-{i:04d}.csv")
    lake.upload_partition(s3, bucket, "payments", date(2019, 1, 1), b"x")
    body = s3.get_object(Bucket=bucket, Key="raw/orders/year=2018/month=01/day=06/part-0001.csv")["Body"].read()
    assert body == b"order_id\n1\n"
    expected = ["year=2017/month=12/day=31", "year=2018/month=01/day=05",
                "year=2018/month=01/day=06", "year=2018/month=02/day=01"]
    assert lake.list_partitions(s3, bucket, "orders") == expected
    # LocalStack 4.4 trả trang rỗng khi ContinuationToken trỏ vào key có ký tự "=" (key Hive như
    # year=2018/...), dù trang đầu báo IsTruncated. S3 thật và moto phân trang đúng, nên chỉ bỏ qua ở LocalStack.
    if s3.backend != "localstack":
        assert lake.list_partitions(s3, bucket, "orders", page_size=2) == expected
    assert lake.list_partitions(s3, bucket, "customers") == []


def test_multipart_roundtrip(s3, bucket):
    data = bytes(range(256)) * (11 * MiB // 256)
    parts = m().multipart_upload(s3, bucket, "raw/orders/big.bin", data, part_size=5 * MiB)
    assert parts == 3
    assert s3.get_object(Bucket=bucket, Key="raw/orders/big.bin")["Body"].read() == data
    assert not s3.list_multipart_uploads(Bucket=bucket).get("Uploads")


def test_apply_lifecycle(s3, bucket):
    if s3.backend == "minio":
        pytest.skip("MinIO cần cấu hình remote tier mới nhận transition GLACIER")
    m().apply_lifecycle(s3, bucket)
    rules = {r["ID"]: r for r in s3.get_bucket_lifecycle_configuration(Bucket=bucket)["Rules"]}
    assert set(rules) == {"raw-tiering", "tmp-expire", "abort-incomplete-mpu"}
    assert rules["tmp-expire"]["Expiration"]["Days"] == 1
