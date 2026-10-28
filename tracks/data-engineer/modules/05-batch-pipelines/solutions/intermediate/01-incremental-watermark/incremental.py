"""Incremental load theo high-watermark: SQLite (nguồn OLTP) -> DuckDB (warehouse).

Bảng nguồn:  orders(order_id TEXT PRIMARY KEY, customer_id TEXT, order_status TEXT, updated_at TEXT)
             updated_at dạng 'YYYY-MM-DD HH:MM:SS'
Bảng đích:   stg_orders(order_id VARCHAR PRIMARY KEY, customer_id VARCHAR,
                        order_status VARCHAR, updated_at TIMESTAMP)
Trạng thái:  etl_state(source VARCHAR PRIMARY KEY, watermark TIMESTAMP)
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import duckdb

SOURCE = "orders"
FMT = "%Y-%m-%d %H:%M:%S"


def init_target(con: duckdb.DuckDBPyConnection) -> None:
    """Tạo bảng đích và bảng trạng thái nếu chưa có (đã làm sẵn)."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS stg_orders (
            order_id VARCHAR PRIMARY KEY,
            customer_id VARCHAR,
            order_status VARCHAR,
            updated_at TIMESTAMP
        )
        """
    )
    con.execute("CREATE TABLE IF NOT EXISTS etl_state (source VARCHAR PRIMARY KEY, watermark TIMESTAMP)")


def get_watermark(con: duckdb.DuckDBPyConnection, source: str = SOURCE) -> datetime | None:
    """Watermark đã lưu cho source, hoặc None nếu chưa chạy lần nào."""
    row = con.execute("SELECT watermark FROM etl_state WHERE source = ?", [source]).fetchone()
    return row[0] if row else None


def extract_since(
    src: sqlite3.Connection, watermark: datetime | None, lookback_minutes: int = 10
) -> list[tuple[str, str, str, str]]:
    """Lấy các dòng có updated_at > watermark - lookback (tất cả nếu watermark None)."""
    sql = "SELECT order_id, customer_id, order_status, updated_at FROM orders"
    params: tuple = ()
    if watermark is not None:
        since = watermark - timedelta(minutes=lookback_minutes)
        sql += " WHERE updated_at > ?"
        params = (since.strftime(FMT),)
    sql += " ORDER BY updated_at, order_id"
    return [tuple(r) for r in src.execute(sql, params).fetchall()]


def upsert(con: duckdb.DuckDBPyConnection, rows: list[tuple[str, str, str, str]]) -> int:
    """INSERT ... ON CONFLICT (order_id) DO UPDATE, chỉ ghi đè khi bản đến mới hơn bản đang có."""
    if not rows:
        return 0
    con.executemany(
        """
        INSERT INTO stg_orders AS t (order_id, customer_id, order_status, updated_at)
        VALUES (?, ?, ?, CAST(? AS TIMESTAMP))
        ON CONFLICT (order_id) DO UPDATE SET
            customer_id = excluded.customer_id,
            order_status = excluded.order_status,
            updated_at = excluded.updated_at
        WHERE excluded.updated_at > t.updated_at
        """,
        rows,
    )
    return len(rows)


def run_incremental(src_path: str, dst_path: str, lookback_minutes: int = 10) -> dict:
    """Một lượt incremental. Trả về {"extracted": n, "watermark": datetime | None}."""
    src = sqlite3.connect(src_path)
    con = duckdb.connect(dst_path)
    try:
        init_target(con)
        old = get_watermark(con)
        rows = extract_since(src, old, lookback_minutes)
        con.execute("BEGIN")
        try:
            upsert(con, rows)
            new = old
            if rows:
                batch_max = max(datetime.strptime(r[3], FMT) for r in rows)
                new = batch_max if old is None else max(old, batch_max)  # không bao giờ lùi
            if new is not None:
                con.execute(
                    """
                    INSERT INTO etl_state VALUES (?, ?)
                    ON CONFLICT (source) DO UPDATE SET watermark = excluded.watermark
                    """,
                    [SOURCE, new],
                )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        return {"extracted": len(rows), "watermark": new}
    finally:
        src.close()
        con.close()
