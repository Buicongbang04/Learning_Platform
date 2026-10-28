"""Làm quen Parquet: ghi, đọc theo cột, đọc thống kê row group, lọc lúc đọc."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pacsv  # noqa: F401
import pyarrow.parquet as pq  # noqa: F401


def csv_to_parquet(csv_path: Path, parquet_path: Path, compression: str = "zstd", row_group_size: int = 1000) -> int:
    """Đổi CSV sang Parquet. Trả về số dòng đã ghi."""
    # TODO: đọc CSV bằng pacsv.read_csv, ghi bằng pq.write_table với compression và row_group_size
    raise NotImplementedError


def read_columns(parquet_path: Path, columns: list[str]) -> pa.Table:
    """Chỉ đọc các cột được yêu cầu (column pruning)."""
    # TODO
    raise NotImplementedError


def row_group_stats(parquet_path: Path, column: str) -> list[tuple]:
    """Trả [(min, max), ...] của `column` cho từng row group, lấy từ metadata."""
    # TODO: dùng pq.ParquetFile(parquet_path).metadata
    raise NotImplementedError


def size_ratio(csv_path: Path, parquet_path: Path) -> float:
    """Dung lượng parquet / dung lượng csv."""
    # TODO
    raise NotImplementedError


def read_expensive_items(parquet_path: Path, min_price: float) -> pa.Table:
    """Các dòng có price >= min_price, lọc ngay lúc đọc bằng filters."""
    # TODO
    raise NotImplementedError
