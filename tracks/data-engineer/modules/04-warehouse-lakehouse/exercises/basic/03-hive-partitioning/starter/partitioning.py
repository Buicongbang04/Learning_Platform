"""Ghi và đọc dữ liệu partition kiểu Hive bằng DuckDB."""

from __future__ import annotations

import shutil  # noqa: F401
from pathlib import Path

import duckdb


def write_partitioned(con: duckdb.DuckDBPyConnection, table: str, out_dir: Path) -> None:
    """Ghi `table` ra out_dir/year=YYYY/month=M/*.parquet, ghi đè nếu đã có."""
    # TODO: xoá out_dir cũ nếu có, rồi COPY ... (FORMAT parquet, PARTITION_BY (year, month))
    raise NotImplementedError


def list_partitions(out_dir: Path) -> list[tuple[int, int]]:
    """[(year, month), ...] tăng dần, đọc từ tên thư mục."""
    # TODO
    raise NotImplementedError


def monthly_revenue(con: duckdb.DuckDBPyConnection, out_dir: Path, year: int, month: int) -> float:
    """Tổng payment_value của đơn delivered trong một tháng."""
    # TODO: read_parquet(..., hive_partitioning = true) WHERE year = ? AND month = ?
    raise NotImplementedError


def revenue_by_month(con: duckdb.DuckDBPyConnection, out_dir: Path) -> list[tuple[int, int, float]]:
    """[(year, month, revenue), ...] tăng dần, chỉ đơn delivered."""
    # TODO
    raise NotImplementedError
