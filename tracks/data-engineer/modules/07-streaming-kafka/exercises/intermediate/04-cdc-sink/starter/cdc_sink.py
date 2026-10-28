"""Áp dụng Debezium envelope và checkpoint Kafka trong một transaction SQLite."""
from __future__ import annotations

import sqlite3

STATUSES = {"created", "approved", "invoiced", "processing", "shipped", "delivered",
            "canceled", "unavailable"}


def initialize(con: sqlite3.Connection) -> None:
    con.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0)
        );
        CREATE TABLE IF NOT EXISTS checkpoints (
            topic TEXT NOT NULL, partition_id INTEGER NOT NULL, last_offset INTEGER NOT NULL,
            PRIMARY KEY(topic, partition_id)
        );
    """)


def apply_record(con, topic: str, partition: int, offset: int,
                 key: dict | None, value: dict | None) -> bool:
    """True nếu offset mới đã commit, False nếu phát lại offset đã xử lý."""
    # TODO: transaction, dedup offset, validate envelope, upsert/delete và checkpoint.
    raise NotImplementedError
