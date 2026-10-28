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


# Dòng hiện hành cần đóng: khách đổi thuộc tính, hoặc khách không còn trong snapshot.
_TO_CLOSE = """
    d.is_current AND (
        EXISTS (
            SELECT 1 FROM stg_customer s
            WHERE s.customer_id = d.customer_id
              AND (s.city IS DISTINCT FROM d.city OR s.state IS DISTINCT FROM d.state)
        )
        OR NOT EXISTS (SELECT 1 FROM stg_customer s WHERE s.customer_id = d.customer_id)
    )
"""


def apply_scd2(con: duckdb.DuckDBPyConnection, snapshot: list[dict], as_of: dt.date) -> dict:
    """Merge snapshot đầy đủ vào dim_customer theo SCD type 2."""
    con.execute("CREATE OR REPLACE TEMP TABLE stg_customer (customer_id VARCHAR, city VARCHAR, state VARCHAR)")
    if snapshot:
        con.executemany(
            "INSERT INTO stg_customer VALUES (?, ?, ?)",
            [(r["customer_id"], r.get("city"), r.get("state")) for r in snapshot],
        )

    con.execute("BEGIN TRANSACTION")
    try:
        closed = con.execute(
            f"""
            UPDATE dim_customer AS d
            SET valid_to = ?, is_current = FALSE
            WHERE {_TO_CLOSE}
            RETURNING customer_key
            """,
            [as_of],
        ).fetchall()

        inserted = con.execute(
            """
            INSERT INTO dim_customer
            SELECT nextval('customer_key_seq'), s.customer_id, s.city, s.state, ?, ?, TRUE
            FROM stg_customer s
            WHERE NOT EXISTS (
                SELECT 1 FROM dim_customer d WHERE d.customer_id = s.customer_id AND d.is_current
            )
            RETURNING customer_key
            """,
            [as_of, HIGH_DATE],
        ).fetchall()
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return {"inserted": len(inserted), "closed": len(closed)}


def lookup_customer_key(con: duckdb.DuckDBPyConnection, customer_id: str, at: dt.date) -> int | None:
    """customer_key của phiên bản có hiệu lực tại ngày `at` (khoảng [valid_from, valid_to))."""
    row = con.execute(
        """
        SELECT customer_key FROM dim_customer
        WHERE customer_id = ? AND valid_from <= ? AND ? < valid_to
        """,
        [customer_id, at, at],
    ).fetchone()
    return row[0] if row else None
