"""Thao tác cơ bản với Delta Lake qua thư viện deltalake (delta-rs)."""

from __future__ import annotations

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake


def create_table(path: str, data: pa.Table) -> int:
    write_deltalake(path, data, mode="error")
    return DeltaTable(path).version()


def append(path: str, data: pa.Table) -> int:
    write_deltalake(path, data, mode="append")
    return DeltaTable(path).version()


def upsert(path: str, updates: pa.Table, key: str = "order_id") -> dict:
    return (
        DeltaTable(path)
        .merge(updates, predicate=f"t.{key} = s.{key}", source_alias="s", target_alias="t")
        .when_matched_update_all()
        .when_not_matched_insert_all()
        .execute()
    )


def read_version(path: str, version: int) -> pa.Table:
    return DeltaTable(path, version=version).to_pyarrow_table().sort_by("order_id")


def history_operations(path: str) -> list[str]:
    return [h["operation"] for h in reversed(DeltaTable(path).history())]


def delete_canceled(path: str) -> int:
    metrics = DeltaTable(path).delete("order_status = 'canceled'")
    return int(metrics["num_deleted_rows"])


def append_with_new_column(path: str, data: pa.Table) -> int:
    write_deltalake(path, data, mode="append", schema_mode="merge")
    return DeltaTable(path).version()
