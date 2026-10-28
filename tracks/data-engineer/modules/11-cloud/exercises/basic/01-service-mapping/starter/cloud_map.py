"""Từ điển dịch vụ data tương đương giữa AWS, Azure và GCP."""

from __future__ import annotations

CLOUDS = ("aws", "azure", "gcp")

CATALOG: dict[str, dict[str, str]] = {
    "compute": {"aws": "EC2", "azure": "Virtual Machines", "gcp": "Compute Engine"},
    "object_storage": {"aws": "S3", "azure": "TODO", "gcp": "TODO"},
    "managed_sql": {"aws": "RDS", "azure": "TODO", "gcp": "Cloud SQL"},
    "etl": {"aws": "Glue", "azure": "TODO", "gcp": "TODO"},
    "warehouse": {"aws": "TODO", "azure": "Synapse Analytics", "gcp": "BigQuery"},
    "streaming": {"aws": "Kinesis", "azure": "TODO", "gcp": "TODO"},
}
# TODO 1: thay mọi "TODO" ở trên bằng tên chuẩn (xem README của bài)

# Cách gọi khác (viết thường) -> tên chuẩn
ALIASES: dict[str, str] = {
    "vm": "Virtual Machines",
    "azure vm": "Virtual Machines",
    "gce": "Compute Engine",
    "gcs": "Cloud Storage",
    "blob": "Blob Storage",
    "aurora": "RDS",
    "azure sql": "SQL Database",
    "adf": "Data Factory",
    "synapse": "Synapse Analytics",
    "kinesis data streams": "Kinesis",
    "pubsub": "Pub/Sub",
}

VENDOR_PREFIXES = ("amazon ", "aws ", "azure ", "google cloud ", "google ", "gcp ")


def lookup(name: str) -> tuple[str, str]:
    """Trả (nhóm, cloud) của một dịch vụ, vd. lookup("Amazon S3") == ("object_storage", "aws")."""
    # TODO 2: chuẩn hoá tên, thử alias, bỏ tiền tố hãng; không tìm thấy -> ValueError
    raise NotImplementedError


def equivalent(name: str, target: str) -> str:
    """Tên chuẩn của dịch vụ tương đương trên cloud target."""
    # TODO 3: dùng lookup(); target không thuộc CLOUDS -> ValueError
    raise NotImplementedError


def comparison_table(categories: list[str] | None = None) -> str:
    """Bảng Markdown | Category | AWS | Azure | GCP |."""
    # TODO 4: header, dòng phân cách, mỗi nhóm một dòng; kết thúc bằng "\n"
    raise NotImplementedError
