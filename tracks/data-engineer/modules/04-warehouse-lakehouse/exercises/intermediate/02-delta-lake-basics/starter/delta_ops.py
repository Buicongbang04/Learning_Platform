"""Thao tác cơ bản với Delta Lake qua thư viện deltalake (delta-rs)."""

from __future__ import annotations

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake  # noqa: F401


def create_table(path: str, data: pa.Table) -> int:
    # TODO: tạo bảng mới (mode="error"), trả version
    raise NotImplementedError


def append(path: str, data: pa.Table) -> int:
    # TODO: mode="append", trả version mới
    raise NotImplementedError


def upsert(path: str, updates: pa.Table, key: str = "order_id") -> dict:
    # TODO: MERGE ... when_matched_update_all ... when_not_matched_insert_all
    raise NotImplementedError


def read_version(path: str, version: int) -> pa.Table:
    # TODO: time travel, sắp theo order_id
    raise NotImplementedError


def history_operations(path: str) -> list[str]:
    # TODO: cũ nhất trước
    raise NotImplementedError


def delete_canceled(path: str) -> int:
    # TODO: trả số dòng đã xoá
    raise NotImplementedError


def append_with_new_column(path: str, data: pa.Table) -> int:
    # TODO: schema evolution khi append
    raise NotImplementedError
