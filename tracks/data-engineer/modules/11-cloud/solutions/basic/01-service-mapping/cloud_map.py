"""Từ điển dịch vụ data tương đương giữa AWS, Azure và GCP."""

from __future__ import annotations

CLOUDS = ("aws", "azure", "gcp")

CATALOG: dict[str, dict[str, str]] = {
    "compute": {"aws": "EC2", "azure": "Virtual Machines", "gcp": "Compute Engine"},
    "object_storage": {"aws": "S3", "azure": "Blob Storage", "gcp": "Cloud Storage"},
    "managed_sql": {"aws": "RDS", "azure": "SQL Database", "gcp": "Cloud SQL"},
    "etl": {"aws": "Glue", "azure": "Data Factory", "gcp": "Dataflow"},
    "warehouse": {"aws": "Redshift", "azure": "Synapse Analytics", "gcp": "BigQuery"},
    "streaming": {"aws": "Kinesis", "azure": "Event Hubs", "gcp": "Pub/Sub"},
}

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

# Dict ngược: tên chuẩn viết thường -> (nhóm, cloud)
_INDEX = {
    service.lower(): (category, cloud)
    for category, by_cloud in CATALOG.items()
    for cloud, service in by_cloud.items()
}


def _candidates(name: str):
    """Sinh các dạng có thể của tên: nguyên bản, rồi bỏ tiền tố hãng (dài trước)."""
    key = " ".join(name.lower().split())
    yield key
    for prefix in sorted(VENDOR_PREFIXES, key=len, reverse=True):
        if key.startswith(prefix):
            yield key[len(prefix):]


def lookup(name: str) -> tuple[str, str]:
    """Trả (nhóm, cloud) của một dịch vụ, vd. lookup("Amazon S3") == ("object_storage", "aws")."""
    for key in _candidates(name):
        key = ALIASES.get(key, key).lower()
        if key in _INDEX:
            return _INDEX[key]
    raise ValueError(f"Không biết dịch vụ {name!r}")


def equivalent(name: str, target: str) -> str:
    """Tên chuẩn của dịch vụ tương đương trên cloud target."""
    target = target.strip().lower()
    if target not in CLOUDS:
        raise ValueError(f"Cloud phải là một trong {CLOUDS}, nhận {target!r}")
    category, _ = lookup(name)
    return CATALOG[category][target]


def comparison_table(categories: list[str] | None = None) -> str:
    """Bảng Markdown | Category | AWS | Azure | GCP |."""
    categories = list(CATALOG) if categories is None else categories
    lines = ["| Category | AWS | Azure | GCP |", "| --- | --- | --- | --- |"]
    for category in categories:
        row = CATALOG[category]
        lines.append(f"| {category} | {row['aws']} | {row['azure']} | {row['gcp']} |")
    return "\n".join(lines) + "\n"
