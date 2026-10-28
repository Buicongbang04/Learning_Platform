"""Lời giải: lớp serving cho API metric có validate, phân trang và cache TTL có version."""

from __future__ import annotations

import datetime as dt
import re
import time

import duckdb

MAX_LIMIT = 500
MAX_RANGE_DAYS = 366
STATE_RE = re.compile(r"^[A-Z]{2}$")


class ValidationError(ValueError):
    """Tham số request không hợp lệ (map sang HTTP 400)."""


class TTLCache:
    def __init__(self, ttl: float, clock=time.monotonic):
        self.ttl = ttl
        self.clock = clock
        self.hits = 0
        self.misses = 0
        self._store: dict = {}

    def get(self, key, default=None):
        entry = self._store.get(key)
        if entry is not None:
            expires_at, value = entry
            if self.clock() < expires_at:
                self.hits += 1
                return value
            del self._store[key]
        self.misses += 1
        return default

    def set(self, key, value) -> None:
        self._store[key] = (self.clock() + self.ttl, value)


def _parse_date(name: str, value) -> dt.date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValidationError(f"{name} phải có dạng YYYY-MM-DD")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{name} không phải ngày hợp lệ") from exc


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class MetricsService:
    def __init__(self, con: duckdb.DuckDBPyConnection, cache: TTLCache, data_version=lambda: "v1"):
        self.con = con
        self.cache = cache
        self.data_version = data_version
        self.queries_executed = 0

    def validate(self, state=None, start=None, end=None, limit=100, offset=0) -> dict:
        if state is not None:
            if not isinstance(state, str) or not STATE_RE.fullmatch(state.upper()):
                raise ValidationError("state phải là mã 2 chữ cái, ví dụ SP")
            state = state.upper()
        if start is None or end is None:
            raise ValidationError("start và end là bắt buộc")
        start_d, end_d = _parse_date("start", start), _parse_date("end", end)
        if start_d > end_d:
            raise ValidationError("start phải <= end")
        if (end_d - start_d).days > MAX_RANGE_DAYS:
            raise ValidationError(f"Khoảng ngày tối đa {MAX_RANGE_DAYS} ngày")
        if not _is_int(limit) or not 1 <= limit <= MAX_LIMIT:
            raise ValidationError(f"limit phải trong 1..{MAX_LIMIT}")
        if not _is_int(offset) or offset < 0:
            raise ValidationError("offset phải >= 0")
        return {"state": state, "start": start_d, "end": end_d, "limit": limit, "offset": offset}

    def get_daily_sales(self, state=None, start=None, end=None, limit=100, offset=0) -> dict:
        p = self.validate(state, start, end, limit, offset)
        version = self.data_version()
        key = ("daily_sales", p["state"], p["start"], p["end"], p["limit"], p["offset"], version)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        where = "order_date BETWEEN ? AND ?"
        params: list = [p["start"], p["end"]]
        if p["state"]:
            where += " AND customer_state = ?"
            params.append(p["state"])

        self.queries_executed += 1
        total = self.con.execute(f"SELECT COUNT(*) FROM agg_daily_sales WHERE {where}", params).fetchone()[0]
        rows = self.con.execute(
            f"""SELECT strftime(order_date, '%Y-%m-%d'), customer_state, orders, revenue
                FROM agg_daily_sales WHERE {where}
                ORDER BY order_date, customer_state
                LIMIT ? OFFSET ?""",
            params + [p["limit"], p["offset"]],
        ).fetchall()
        body = {
            "data": [
                {"order_date": d, "customer_state": s, "orders": int(o), "revenue": float(r)}
                for d, s, o, r in rows
            ],
            "total": int(total),
            "limit": p["limit"],
            "offset": p["offset"],
            "data_version": version,
        }
        self.cache.set(key, body)
        return body


def handle_request(service: MetricsService, query: dict[str, str]) -> tuple[int, dict]:
    try:
        limit = int(query.get("limit", "100"))
        offset = int(query.get("offset", "0"))
    except ValueError:
        return 400, {"error": "limit và offset phải là số nguyên"}
    try:
        body = service.get_daily_sales(
            state=query.get("state"), start=query.get("start"), end=query.get("end"),
            limit=limit, offset=offset,
        )
    except ValidationError as exc:
        return 400, {"error": str(exc)}
    return 200, body
