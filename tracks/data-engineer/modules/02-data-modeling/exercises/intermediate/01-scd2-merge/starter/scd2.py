"""SCD type 2 cho dim_customer (DuckDB)."""

from __future__ import annotations

import datetime as dt

import duckdb

HIGH_DATE = dt.date(9999, 12, 31)


def create_dim_customer(con: duckdb.DuckDBPyConnection) -> None:
    """Đã làm sẵn."""
    con.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS customer_key_seq START 1;
        CREATE TABLE IF NOT EXISTS dim_customer (
            customer_key INTEGER PRIMARY KEY,
            customer_id  VARCHAR NOT NULL,
            city         VARCHAR,
            state        VARCHAR,
            valid_from   DATE NOT NULL,
            valid_to     DATE NOT NULL,
            is_current   BOOLEAN NOT NULL
        );
        """
    )


def apply_scd2(con: duckdb.DuckDBPyConnection, snapshot: list[dict], as_of: dt.date) -> dict:
    """Merge snapshot đầy đủ vào dim_customer theo SCD type 2.

    Trả về {"inserted": n, "closed": m}.
    """
    # TODO: stage snapshot, đóng dòng đổi/bị xoá, chèn phiên bản mới; tất cả trong một transaction
    raise NotImplementedError


def lookup_customer_key(con: duckdb.DuckDBPyConnection, customer_id: str, at: dt.date) -> int | None:
    """customer_key của phiên bản có hiệu lực tại ngày `at` (khoảng [valid_from, valid_to))."""
    # TODO
    raise NotImplementedError
