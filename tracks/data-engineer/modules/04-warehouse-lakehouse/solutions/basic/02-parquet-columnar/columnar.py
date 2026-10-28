"""Làm quen Parquet: ghi, đọc theo cột, đọc thống kê row group, lọc lúc đọc."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq


def csv_to_parquet(csv_path: Path, parquet_path: Path, compression: str = "zstd", row_group_size: int = 1000) -> int:
    """Đổi CSV sang Parquet. Trả về số dòng đã ghi."""
    table = pacsv.read_csv(csv_path)
    pq.write_table(table, parquet_path, compression=compression, row_group_size=row_group_size)
    return table.num_rows


def read_columns(parquet_path: Path, columns: list[str]) -> pa.Table:
    """Chỉ đọc các cột được yêu cầu (column pruning)."""
    return pq.read_table(parquet_path, columns=columns)


def row_group_stats(parquet_path: Path, column: str) -> list[tuple]:
    """Trả [(min, max), ...] của `column` cho từng row group, lấy từ metadata."""
    meta = pq.ParquetFile(parquet_path).metadata
    idx = meta.schema.names.index(column)
    result = []
    for i in range(meta.num_row_groups):
        stats = meta.row_group(i).column(idx).statistics
        result.append((stats.min, stats.max))
    return result


def size_ratio(csv_path: Path, parquet_path: Path) -> float:
    """Dung lượng parquet / dung lượng csv."""
    return Path(parquet_path).stat().st_size / Path(csv_path).stat().st_size


def read_expensive_items(parquet_path: Path, min_price: float) -> pa.Table:
    """Các dòng có price >= min_price, lọc ngay lúc đọc bằng filters."""
    return pq.read_table(parquet_path, filters=[("price", ">=", min_price)])
