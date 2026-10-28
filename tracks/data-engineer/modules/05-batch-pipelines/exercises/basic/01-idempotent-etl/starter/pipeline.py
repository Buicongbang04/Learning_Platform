"""Pipeline ETL idempotent: CSV đơn hàng -> DuckDB, tham số hoá theo ngày `ds`."""

from __future__ import annotations

import duckdb
import pandas as pd

COLUMNS = ["order_id", "customer_id", "order_status", "amount", "ds"]


def extract(csv_path: str) -> pd.DataFrame:
    """Đọc CSV, mọi cột giữ kiểu chuỗi."""
    # TODO: đọc csv_path bằng pandas với dtype=str
    raise NotImplementedError


def transform(df: pd.DataFrame, ds: str) -> pd.DataFrame:
    """Lọc theo ngày ds, bỏ dòng thiếu order_id, chuẩn hoá status/amount, dedup theo order_id."""
    # TODO: trả về DataFrame với các cột COLUMNS, index 0..n-1
    raise NotImplementedError


def load(con: duckdb.DuckDBPyConnection, df: pd.DataFrame, ds: str) -> int:
    """Delete-insert partition ds trong một transaction. Trả về số dòng đã chèn."""
    # TODO: CREATE TABLE IF NOT EXISTS fct_orders(...), BEGIN, DELETE ds, INSERT, COMMIT
    # (ROLLBACK và raise lại nếu lỗi)
    raise NotImplementedError


def run(csv_path: str, db_path: str, ds: str) -> int:
    """Chạy extract -> transform -> load cho một ngày."""
    # TODO: mở duckdb.connect(db_path), gọi 3 bước, đóng kết nối
    raise NotImplementedError
