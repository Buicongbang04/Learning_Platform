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
    # TODO
    raise NotImplementedError


def extract_since(
    src: sqlite3.Connection, watermark: datetime | None, lookback_minutes: int = 10
) -> list[tuple[str, str, str, str]]:
    """Lấy các dòng có updated_at > watermark - lookback (tất cả nếu watermark None).

    Trả về list tuple (order_id, customer_id, order_status, updated_at) sắp theo updated_at.
    """
    # TODO: tính mốc = watermark - timedelta(minutes=lookback_minutes), so sánh chuỗi 'YYYY-MM-DD HH:MM:SS'
    raise NotImplementedError


def upsert(con: duckdb.DuckDBPyConnection, rows: list[tuple[str, str, str, str]]) -> int:
    """INSERT ... ON CONFLICT (order_id) DO UPDATE, chỉ ghi đè khi bản đến mới hơn bản đang có.

    Trả về số dòng đã gửi vào upsert. Không tự BEGIN/COMMIT (run_incremental lo transaction).
    """
    # TODO
    raise NotImplementedError


def run_incremental(src_path: str, dst_path: str, lookback_minutes: int = 10) -> dict:
    """Một lượt incremental. Trả về {"extracted": n, "watermark": datetime | None}.

    Thứ tự: đọc watermark -> extract -> BEGIN -> upsert(...) -> cập nhật watermark = max(updated_at)
    (không bao giờ lùi) -> COMMIT. Lỗi thì ROLLBACK và raise lại.
    Gọi `upsert` qua tên hàm của module (test sẽ thay hàm này để giả lập lỗi).
    """
    # TODO
    raise NotImplementedError
