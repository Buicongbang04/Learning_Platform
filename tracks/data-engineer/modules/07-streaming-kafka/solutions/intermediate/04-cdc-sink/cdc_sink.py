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
    con.execute("BEGIN IMMEDIATE")
    try:
        previous = con.execute(
            "SELECT last_offset FROM checkpoints WHERE topic=? AND partition_id=?",
            (topic, partition),
        ).fetchone()
        if previous and offset <= previous[0]:
            con.rollback()
            return False
        if value is not None:
            if (not isinstance(value, dict) or not isinstance(value.get("op"), str)
                    or value["op"] not in {"r", "c", "u", "d"}):
                raise ValueError("Envelope/op không được hỗ trợ")
            if not isinstance(key, dict) or not isinstance(key.get("order_id"), str) or not key["order_id"]:
                raise ValueError("Thiếu order_id trong Kafka key")
            order_id = key["order_id"]
            if value["op"] == "d":
                con.execute("DELETE FROM orders WHERE order_id=?", (order_id,))
            else:
                after = value.get("after")
                if not isinstance(after, dict) or after.get("order_id") != order_id:
                    raise ValueError("after thiếu hoặc order_id không khớp key")
                status, amount = after.get("status"), after.get("amount_cents")
                if (not isinstance(status, str) or status not in STATUSES
                        or type(amount) is not int or amount < 0):
                    raise ValueError("status/amount_cents không hợp lệ")
                con.execute("""
                    INSERT INTO orders VALUES (?, ?, ?)
                    ON CONFLICT(order_id) DO UPDATE SET
                    status=excluded.status, amount_cents=excluded.amount_cents
                """, (order_id, status, amount))
        # Tombstone không sửa orders nhưng vẫn ghi nhận tiến độ của record này.
        con.execute("""
            INSERT INTO checkpoints VALUES (?, ?, ?)
            ON CONFLICT(topic, partition_id) DO UPDATE SET last_offset=excluded.last_offset
        """, (topic, partition, offset))
        con.commit()
        return True
    except Exception:
        con.rollback()
        raise
