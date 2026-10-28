"""Ghi và đọc các bảng Cassandra thiết kế theo truy vấn."""

from __future__ import annotations

import re
from collections import defaultdict  # noqa: F401
from datetime import date, datetime  # noqa: F401
from decimal import Decimal  # noqa: F401


def split_statements(cql: str) -> list[str]:
    """Bỏ comment `--`/`//` và tách theo dấu ; (đã viết sẵn)."""
    text = re.sub(r"(--|//)[^\n]*", "", cql)
    return [s.strip() for s in text.split(";") if s.strip()]


def seller_order_rows(orders: list[dict]) -> list[dict]:
    """Một dòng cho mỗi cặp (đơn, seller), sắp theo (seller_id, purchased_at, order_id)."""
    # TODO: gom price theo seller trong từng đơn; order_date = purchased_at.date()
    raise NotImplementedError


def insert_events(session, events: list[dict]) -> None:
    """events: {order_id, event_time, event_type, location}."""
    # TODO: prepare INSERT một lần, execute cho từng event
    raise NotImplementedError


def insert_seller_orders(session, rows: list[dict]) -> None:
    # TODO: prepare INSERT vào orders_by_seller_day; order_value nên là Decimal(str(value))
    raise NotImplementedError


def order_history(session, order_id: str, limit: int = 10) -> list[tuple[datetime, str]]:
    # TODO: SELECT event_time, event_type ... WHERE order_id = ? LIMIT ?
    raise NotImplementedError


def seller_orders(session, seller_id: str, day: date, limit: int = 20) -> list[str]:
    # TODO: SELECT order_id ... WHERE seller_id = ? AND order_date = ? LIMIT ?
    raise NotImplementedError
