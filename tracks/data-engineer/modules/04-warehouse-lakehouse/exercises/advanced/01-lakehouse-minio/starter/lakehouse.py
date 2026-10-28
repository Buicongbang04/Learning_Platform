"""Mini lakehouse: bronze/silver/gold là bảng Delta, chạy trên local hoặc S3 (MinIO).

TODO (trả lời ngắn, thay đoạn này):
- Vì sao bronze là append-only?
- Vì sao gold ở đây ghi đè toàn phần, còn ở quy mô lớn thì không nên?
"""

from __future__ import annotations

import duckdb  # noqa: F401
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake  # noqa: F401


def table_uri(root: str, layer: str, name: str) -> str:
    return f"{str(root).rstrip('/')}/{layer}/{name}"


def ingest_bronze(root: str, raw: pa.Table, batch_id: str, storage_options: dict | None = None) -> int:
    """Append raw vào bronze/orders kèm _batch_id, _ingested_at. Idempotent theo batch_id."""
    # TODO
    raise NotImplementedError


def refresh_silver(root: str, storage_options: dict | None = None) -> int:
    """Bronze -> silver/orders: ép kiểu, làm sạch, khử trùng, MERGE chỉ khi updated_at mới hơn."""
    # TODO
    raise NotImplementedError


def refresh_gold(root: str, storage_options: dict | None = None) -> int:
    """Silver -> gold/revenue_by_state_month (ghi đè)."""
    # TODO
    raise NotImplementedError


def query(root: str, sql: str, storage_options: dict | None = None) -> list[tuple]:
    """Chạy SQL trên các view bronze_orders, silver_orders, gold_revenue."""
    # TODO
    raise NotImplementedError
