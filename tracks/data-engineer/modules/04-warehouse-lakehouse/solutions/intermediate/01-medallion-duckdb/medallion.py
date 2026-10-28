"""Medallion: bronze (thô) -> silver (sạch) -> gold (tổng hợp), lưu Parquet."""

from __future__ import annotations

from pathlib import Path

import duckdb


def _count(con: duckdb.DuckDBPyConnection, path: Path) -> int:
    return con.execute(f"SELECT count(*) FROM read_parquet('{path}')").fetchone()[0]


def load_bronze(con: duckdb.DuckDBPyConnection, csv_path: Path, bronze_dir: Path) -> int:
    """CSV -> bronze_dir/orders.parquet, mọi cột VARCHAR + _source_file + _ingested_at."""
    Path(bronze_dir).mkdir(parents=True, exist_ok=True)
    out = Path(bronze_dir) / "orders.parquet"
    con.execute(
        f"""
        COPY (
            SELECT *,
                   ? AS _source_file,
                   current_timestamp::TIMESTAMP AS _ingested_at
            FROM read_csv('{csv_path}', all_varchar = true, header = true)
        ) TO '{out}' (FORMAT parquet)
        """,
        [Path(csv_path).name],
    )
    return _count(con, out)


def build_silver(con: duckdb.DuckDBPyConnection, bronze_dir: Path, silver_dir: Path) -> int:
    """Bronze -> silver_dir/orders.parquet: ép kiểu, chuẩn hoá, lọc dòng hỏng, giữ bản mới nhất."""
    Path(silver_dir).mkdir(parents=True, exist_ok=True)
    src = Path(bronze_dir) / "orders.parquet"
    out = Path(silver_dir) / "orders.parquet"
    con.execute(
        f"""
        COPY (
            WITH typed AS (
                SELECT
                    trim(order_id)                              AS order_id,
                    trim(customer_id)                           AS customer_id,
                    lower(trim(order_status))                   AS order_status,
                    TRY_CAST(order_purchase_timestamp AS TIMESTAMP) AS order_purchase_timestamp,
                    TRY_CAST(order_value AS DOUBLE)             AS order_value,
                    TRY_CAST(updated_at AS TIMESTAMP)           AS updated_at
                FROM read_parquet('{src}')
            )
            SELECT *
            FROM typed
            WHERE order_id IS NOT NULL AND order_id <> ''
              AND order_purchase_timestamp IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY updated_at DESC NULLS LAST) = 1
            ORDER BY order_id
        ) TO '{out}' (FORMAT parquet)
        """
    )
    return _count(con, out)


def build_gold(con: duckdb.DuckDBPyConnection, silver_dir: Path, gold_dir: Path) -> int:
    """Silver -> gold_dir/daily_revenue.parquet (order_date, delivered_orders, revenue)."""
    Path(gold_dir).mkdir(parents=True, exist_ok=True)
    src = Path(silver_dir) / "orders.parquet"
    out = Path(gold_dir) / "daily_revenue.parquet"
    con.execute(
        f"""
        COPY (
            SELECT
                CAST(order_purchase_timestamp AS DATE) AS order_date,
                COUNT(*)                               AS delivered_orders,
                SUM(order_value)                       AS revenue
            FROM read_parquet('{src}')
            WHERE order_status = 'delivered'
            GROUP BY 1
            ORDER BY 1
        ) TO '{out}' (FORMAT parquet)
        """
    )
    return _count(con, out)
