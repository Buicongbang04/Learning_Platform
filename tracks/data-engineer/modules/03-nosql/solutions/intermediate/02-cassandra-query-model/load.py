"""Lời giải: ghi và đọc các bảng Cassandra thiết kế theo truy vấn."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal


def split_statements(cql: str) -> list[str]:
    text = re.sub(r"(--|//)[^\n]*", "", cql)
    return [s.strip() for s in text.split(";") if s.strip()]


def seller_order_rows(orders: list[dict]) -> list[dict]:
    rows = []
    for order in orders:
        per_seller: dict[str, float] = defaultdict(float)
        for item in order["items"]:
            per_seller[item["seller_id"]] += item["price"]
        for seller_id, value in per_seller.items():
            rows.append(
                {
                    "seller_id": seller_id,
                    "order_date": order["purchased_at"].date(),
                    "purchased_at": order["purchased_at"],
                    "order_id": order["order_id"],
                    "order_value": round(value, 2),
                }
            )
    rows.sort(key=lambda r: (r["seller_id"], r["purchased_at"], r["order_id"]))
    return rows


def insert_events(session, events: list[dict]) -> None:
    stmt = session.prepare(
        "INSERT INTO order_events_by_order (order_id, event_time, event_type, location) VALUES (?, ?, ?, ?)"
    )
    for e in events:
        session.execute(stmt, (e["order_id"], e["event_time"], e["event_type"], e.get("location")))


def insert_seller_orders(session, rows: list[dict]) -> None:
    stmt = session.prepare(
        "INSERT INTO orders_by_seller_day (seller_id, order_date, purchased_at, order_id, order_value) "
        "VALUES (?, ?, ?, ?, ?)"
    )
    for r in rows:
        session.execute(
            stmt,
            (r["seller_id"], r["order_date"], r["purchased_at"], r["order_id"], Decimal(str(r["order_value"]))),
        )


def order_history(session, order_id: str, limit: int = 10) -> list[tuple[datetime, str]]:
    stmt = session.prepare(
        "SELECT event_time, event_type FROM order_events_by_order WHERE order_id = ? LIMIT ?"
    )
    return [(row.event_time, row.event_type) for row in session.execute(stmt, (order_id, limit))]


def seller_orders(session, seller_id: str, day: date, limit: int = 20) -> list[str]:
    stmt = session.prepare(
        "SELECT order_id FROM orders_by_seller_day WHERE seller_id = ? AND order_date = ? LIMIT ?"
    )
    return [row.order_id for row in session.execute(stmt, (seller_id, day, limit))]
