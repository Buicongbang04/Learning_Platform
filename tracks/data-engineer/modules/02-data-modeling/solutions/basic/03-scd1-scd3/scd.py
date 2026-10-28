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


def _stage(con: duckdb.DuckDBPyConnection, rows: list[dict]) -> None:
    con.execute("CREATE OR REPLACE TEMP TABLE stg_seller (seller_id VARCHAR, city VARCHAR, state VARCHAR)")
    if rows:
        con.executemany(
            "INSERT INTO stg_seller VALUES (?, ?, ?)",
            [(r["seller_id"], r["city"], r["state"]) for r in rows],
        )


def apply_scd1(con: duckdb.DuckDBPyConnection, rows: list[dict]) -> None:
    """Upsert: thêm seller mới, ghi đè city/state của seller đã có."""
    _stage(con, rows)
    con.execute(
        """
        INSERT INTO dim_seller
        SELECT seller_id, city, state FROM stg_seller
        ON CONFLICT (seller_id) DO UPDATE
        SET city = excluded.city, state = excluded.state
        """
    )


def apply_scd3(con: duckdb.DuckDBPyConnection, rows: list[dict], as_of: dt.date) -> None:
    """Giữ bang hiện tại và bang ngay trước đó."""
    _stage(con, rows)
    con.execute("BEGIN TRANSACTION")
    try:
        # Vế phải của SET đọc giá trị cũ của dòng, nên previous_state nhận bang cũ.
        con.execute(
            """
            UPDATE dim_seller_scd3 AS d
            SET previous_state   = d.current_state,
                current_state    = s.state,
                state_changed_on = ?
            FROM stg_seller AS s
            WHERE d.seller_id = s.seller_id
              AND d.current_state IS DISTINCT FROM s.state
            """,
            [as_of],
        )
        con.execute(
            """
            INSERT INTO dim_seller_scd3 (seller_id, current_state, previous_state, state_changed_on)
            SELECT s.seller_id, s.state, NULL, NULL
            FROM stg_seller AS s
            WHERE NOT EXISTS (SELECT 1 FROM dim_seller_scd3 d WHERE d.seller_id = s.seller_id)
            """
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
