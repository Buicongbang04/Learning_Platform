"""Ghi và đọc dữ liệu partition kiểu Hive bằng DuckDB."""

from __future__ import annotations

import shutil
from pathlib import Path

import duckdb


def _glob(out_dir: Path) -> str:
    return str(Path(out_dir) / "**" / "*.parquet")


def write_partitioned(con: duckdb.DuckDBPyConnection, table: str, out_dir: Path) -> None:
    """Ghi `table` ra out_dir/year=YYYY/month=M/*.parquet, ghi đè nếu đã có."""
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    con.execute(
        f"""
        COPY (
            SELECT *,
                   year(order_purchase_timestamp)  AS year,
                   month(order_purchase_timestamp) AS month
            FROM {table}
        ) TO '{out_dir}' (FORMAT parquet, PARTITION_BY (year, month))
        """
    )


def list_partitions(out_dir: Path) -> list[tuple[int, int]]:
    """[(year, month), ...] tăng dần, đọc từ tên thư mục."""
    result = []
    for year_dir in Path(out_dir).glob("year=*"):
        year = int(year_dir.name.split("=", 1)[1])
        for month_dir in year_dir.glob("month=*"):
            result.append((year, int(month_dir.name.split("=", 1)[1])))
    return sorted(result)


def monthly_revenue(con: duckdb.DuckDBPyConnection, out_dir: Path, year: int, month: int) -> float:
    """Tổng payment_value của đơn delivered trong một tháng."""
    row = con.execute(
        f"""
        SELECT COALESCE(SUM(payment_value), 0)
        FROM read_parquet('{_glob(out_dir)}', hive_partitioning = true)
        WHERE year = ? AND month = ? AND order_status = 'delivered'
        """,
        [year, month],
    ).fetchone()
    return float(row[0])


def revenue_by_month(con: duckdb.DuckDBPyConnection, out_dir: Path) -> list[tuple[int, int, float]]:
    """[(year, month, revenue), ...] tăng dần, chỉ đơn delivered."""
    rows = con.execute(
        f"""
        SELECT year, month, SUM(payment_value) AS revenue
        FROM read_parquet('{_glob(out_dir)}', hive_partitioning = true)
        WHERE order_status = 'delivered'
        GROUP BY year, month
        ORDER BY year, month
        """
    ).fetchall()
    return [(int(y), int(m), float(r)) for y, m, r in rows]
