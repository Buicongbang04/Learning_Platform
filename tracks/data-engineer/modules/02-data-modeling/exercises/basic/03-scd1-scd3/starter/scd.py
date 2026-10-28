"""SCD type 1 và type 3 cho dimension seller (DuckDB)."""

from __future__ import annotations

import datetime as dt

import duckdb


def create_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Đã làm sẵn: tạo hai bảng dimension."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_seller (
            seller_id VARCHAR PRIMARY KEY, city VARCHAR, state VARCHAR
        );
        CREATE TABLE IF NOT EXISTS dim_seller_scd3 (
            seller_id VARCHAR PRIMARY KEY, current_state VARCHAR,
            previous_state VARCHAR, state_changed_on DATE
        );
        """
    )


def apply_scd1(con: duckdb.DuckDBPyConnection, rows: list[dict]) -> None:
    """Upsert: thêm seller mới, ghi đè city/state của seller đã có."""
    # TODO: nạp rows vào bảng tạm rồi INSERT ... ON CONFLICT DO UPDATE
    raise NotImplementedError


def apply_scd3(con: duckdb.DuckDBPyConnection, rows: list[dict], as_of: dt.date) -> None:
    """Giữ bang hiện tại và bang ngay trước đó."""
    # TODO: UPDATE seller đổi bang (previous_state, current_state, state_changed_on), INSERT seller mới
    raise NotImplementedError
