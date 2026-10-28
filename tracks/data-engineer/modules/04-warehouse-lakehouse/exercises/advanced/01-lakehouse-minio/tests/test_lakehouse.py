import uuid
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import DeltaTable

import testkit
from testkit import Exercise, use_solution

if use_solution():
    pytest.skip("Bài advanced không có lời giải chạy được; xem SOLUTION.md", allow_module_level=True)

ex = Exercise(__file__)
COLS = ["order_id", "customer_state", "order_status", "order_purchase_timestamp", "order_value", "updated_at"]

BATCH_1 = [
    ("o1", "SP", "processing", "2024-03-01 10:00:00", "100.0", "2024-03-01 10:00:00"),
    ("o2", "RJ", "delivered", "2024-03-02 11:00:00", "80.0", "2024-03-06 09:00:00"),
    ("o3", "SP", "delivered", "2024-04-05 09:00:00", "50.5", "2024-04-05 09:00:00"),
    ("", "SP", "delivered", "2024-04-05 09:00:00", "999", "2024-04-05 09:00:00"),
    ("o9", "MG", "delivered", "bad-date", "10", "2024-04-05 09:00:00"),
]
BATCH_2 = [
    ("o1", "SP", "delivered", "2024-03-01 10:00:00", "100.0", "2024-03-05 08:00:00"),
    ("o4", "MG", "delivered", "2024-04-10 15:00:00", "40.0", "2024-04-10 15:00:00"),
    ("o4", "MG", "delivered", "2024-04-10 15:00:00", "40.0", "2024-04-10 15:00:00"),
]
# Bản cũ của o2 đến trễ: không được ghi đè bản delivered
BATCH_LATE = [
    ("o2", "RJ", "shipped", "2024-03-02 11:00:00", "80.0", "2024-03-02 11:30:00"),
]


def raw(rows):
    return pa.table({c: pa.array([r[i] for r in rows], pa.string()) for i, c in enumerate(COLS)})


@pytest.fixture(scope="module")
def lh():
    return ex.module("lakehouse.py")


def run_pipeline(lh, root, opts=None):
    assert lh.ingest_bronze(root, raw(BATCH_1), "b1", opts) == 5
    assert lh.ingest_bronze(root, raw(BATCH_1), "b1", opts) == 0
    lh.refresh_silver(root, opts)
    assert lh.ingest_bronze(root, raw(BATCH_2), "b2", opts) == 3
    lh.refresh_silver(root, opts)
    assert lh.ingest_bronze(root, raw(BATCH_LATE), "b3", opts) == 1
    n = lh.refresh_silver(root, opts)
    lh.refresh_gold(root, opts)
    return n


def check_results(lh, root, opts=None):
    assert lh.query(root, "SELECT count(*) FROM bronze_orders", opts) == [(9,)]
    assert lh.query(root, "SELECT count(DISTINCT _batch_id) FROM bronze_orders", opts) == [(3,)]
    status = dict(lh.query(root, "SELECT order_id, order_status FROM silver_orders", opts))
    assert status == {"o1": "delivered", "o2": "delivered", "o3": "delivered", "o4": "delivered"}
    gold = lh.query(
        root,
        "SELECT customer_state, year_month, delivered_orders, revenue FROM gold_revenue ORDER BY 1, 2",
        opts,
    )
    assert gold == [
        ("MG", "2024-04", 1, pytest.approx(40.0)),
        ("RJ", "2024-03", 1, pytest.approx(80.0)),
        ("SP", "2024-03", 1, pytest.approx(100.0)),
        ("SP", "2024-04", 1, pytest.approx(50.5)),
    ]


def test_pipeline_local(lh, tmp_path):
    root = str(tmp_path / "lake")
    assert run_pipeline(lh, root) == 4
    check_results(lh, root)
    for layer, name in [("bronze", "orders"), ("silver", "orders"), ("gold", "revenue_by_state_month")]:
        assert (Path(root) / layer / name / "_delta_log").is_dir()
    ops = [h["operation"] for h in DeltaTable(lh.table_uri(root, "silver", "orders")).history()]
    assert "MERGE" in ops


def test_silver_types(lh, tmp_path):
    root = str(tmp_path / "lake")
    run_pipeline(lh, root)
    schema = DeltaTable(lh.table_uri(root, "silver", "orders")).to_pyarrow_table().schema
    assert pa.types.is_timestamp(schema.field("order_purchase_timestamp").type)
    assert pa.types.is_timestamp(schema.field("updated_at").type)
    assert pa.types.is_floating(schema.field("order_value").type)


def test_reruns_are_idempotent(lh, tmp_path):
    root = str(tmp_path / "lake")
    run_pipeline(lh, root)
    assert lh.refresh_silver(root) == 4
    assert lh.refresh_gold(root) == 4
    check_results(lh, root)


def test_pipeline_on_minio(lh):
    ex.require_service("minio")
    import boto3

    bucket = f"lakehouse-test-{uuid.uuid4().hex[:8]}"
    key, secret = testkit.MINIO_AUTH
    from botocore.exceptions import ClientError

    s3 = boto3.client(
        "s3", endpoint_url=testkit.MINIO_ENDPOINT, aws_access_key_id=key, aws_secret_access_key=secret,
        region_name="us-east-1",
    )
    try:
        s3.create_bucket(Bucket=bucket)
    except ClientError as err:  # cổng 9000 có S3 khác, không nhận minioadmin
        pytest.skip(f"MinIO ở {testkit.MINIO_ENDPOINT} không nhận tài khoản minioadmin: {err}")
    opts = {
        "AWS_ENDPOINT_URL": testkit.MINIO_ENDPOINT,
        "AWS_ACCESS_KEY_ID": key,
        "AWS_SECRET_ACCESS_KEY": secret,
        "AWS_REGION": "us-east-1",
        "AWS_ALLOW_HTTP": "true",
        "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
    }
    root = f"s3://{bucket}/olist"
    assert run_pipeline(lh, root, opts) == 4
    check_results(lh, root, opts)
