"""Rate limiter, leaderboard và HyperLogLog bằng Redis."""

from __future__ import annotations

from uuid import uuid4  # noqa: F401

DAY_SECONDS = 86_400


def fixed_window_allow(r, client_id: str, limit: int, window: int, now: float) -> bool:
    # TODO: key rl:fixed:<client_id>:<int(now // window)>; pipeline INCR + EXPIRE
    raise NotImplementedError


def sliding_window_allow(
    r, client_id: str, limit: int, window: int, now: float, request_id: str
) -> bool:
    # TODO: ZREMRANGEBYSCORE cũ, ZCARD, nếu còn chỗ thì ZADD + EXPIRE
    raise NotImplementedError


def record_sale(r, product_id: str, qty: int, day: str) -> None:
    # TODO: ZINCRBY top:<day>, EXPIRE 8 ngày
    raise NotImplementedError


def top_sellers(r, day: str, k: int = 10) -> list[tuple[str, int]]:
    # TODO: ZREVRANGE ... WITHSCORES, đổi điểm sang int
    raise NotImplementedError


def top_sellers_over(r, days: list[str], k: int = 10) -> list[tuple[str, int]]:
    # TODO: ZUNIONSTORE vào key tạm, đọc, xoá key tạm
    raise NotImplementedError


def track_visit(r, day: str, visitor_id: str) -> None:
    # TODO: PFADD uv:<day>
    raise NotImplementedError


def count_visitors(r, days: list[str]) -> int:
    # TODO: PFCOUNT trên nhiều key
    raise NotImplementedError
