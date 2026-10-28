"""Lời giải: rate limiter, leaderboard và HyperLogLog bằng Redis."""

from __future__ import annotations

from uuid import uuid4

DAY_SECONDS = 86_400


def fixed_window_allow(r, client_id: str, limit: int, window: int, now: float) -> bool:
    key = f"rl:fixed:{client_id}:{int(now // window)}"
    pipe = r.pipeline()  # transaction=True: MULTI ... EXEC
    pipe.incr(key)
    pipe.expire(key, window)
    count, _ = pipe.execute()
    return count <= limit


def sliding_window_allow(
    r, client_id: str, limit: int, window: int, now: float, request_id: str
) -> bool:
    # Lưu ý: giữa ZCARD và ZADD có thể có client khác chen vào (check-then-act).
    # Production nên gói cả đoạn này vào một Lua script (EVAL) để Redis chạy nguyên tử.
    key = f"rl:sliding:{client_id}"
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, "-inf", now - window)
    pipe.zcard(key)
    _, count = pipe.execute()
    if count >= limit:
        return False
    pipe = r.pipeline()
    pipe.zadd(key, {request_id: now})
    pipe.expire(key, window)
    pipe.execute()
    return True


def record_sale(r, product_id: str, qty: int, day: str) -> None:
    key = f"top:{day}"
    pipe = r.pipeline()
    pipe.zincrby(key, qty, product_id)
    pipe.expire(key, 8 * DAY_SECONDS)
    pipe.execute()


def _as_pairs(rows) -> list[tuple[str, int]]:
    return [(member, int(score)) for member, score in rows]


def top_sellers(r, day: str, k: int = 10) -> list[tuple[str, int]]:
    return _as_pairs(r.zrevrange(f"top:{day}", 0, k - 1, withscores=True))


def top_sellers_over(r, days: list[str], k: int = 10) -> list[tuple[str, int]]:
    tmp = f"tmp:top:{uuid4().hex}"
    pipe = r.pipeline()
    pipe.zunionstore(tmp, [f"top:{d}" for d in days])
    pipe.zrevrange(tmp, 0, k - 1, withscores=True)
    pipe.delete(tmp)
    _, rows, _ = pipe.execute()
    return _as_pairs(rows)


def track_visit(r, day: str, visitor_id: str) -> None:
    r.pfadd(f"uv:{day}", visitor_id)


def count_visitors(r, days: list[str]) -> int:
    return r.pfcount(*[f"uv:{d}" for d in days])
