"""Medallion: bronze (thô) -> silver (sạch) -> gold (tổng hợp), lưu Parquet."""

from __future__ import annotations

from pathlib import Path

import duckdb


def load_bronze(con: duckdb.DuckDBPyConnection, csv_path: Path, bronze_dir: Path) -> int:
    """CSV -> bronze_dir/orders.parquet, mọi cột VARCHAR + _source_file + _ingested_at."""
    Path(bronze_dir).mkdir(parents=True, exist_ok=True)
    # TODO: read_csv(..., all_varchar = true), thêm 2 cột metadata, COPY ra parquet, trả số dòng
    raise NotImplementedError


def build_silver(con: duckdb.DuckDBPyConnection, bronze_dir: Path, silver_dir: Path) -> int:
    """Bronze -> silver_dir/orders.parquet: ép kiểu, chuẩn hoá, lọc dòng hỏng, giữ bản mới nhất."""
    Path(silver_dir).mkdir(parents=True, exist_ok=True)
    # TODO: TRY_CAST, trim/lower, lọc order_id rỗng và timestamp hỏng, QUALIFY ROW_NUMBER() ... = 1
    raise NotImplementedError


def build_gold(con: duckdb.DuckDBPyConnection, silver_dir: Path, gold_dir: Path) -> int:
    """Silver -> gold_dir/daily_revenue.parquet (order_date, delivered_orders, revenue)."""
    Path(gold_dir).mkdir(parents=True, exist_ok=True)
    # TODO
    raise NotImplementedError
