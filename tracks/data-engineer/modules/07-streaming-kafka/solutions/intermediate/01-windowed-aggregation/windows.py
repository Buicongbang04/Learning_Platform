"""Tumbling và hopping window aggregation theo event time (giây epoch)."""

from __future__ import annotations

from collections import defaultdict


def tumbling_window_start(ts: int, size: int) -> int:
    if size <= 0:
        raise ValueError("size phải > 0")
    return ts - ts % size


def hopping_window_starts(ts: int, size: int, advance: int) -> list[int]:
    """Mọi window [s, s+size) chứa ts, với s chia hết cho advance và s >= 0. Tăng dần."""
    if size <= 0 or advance <= 0 or advance > size:
        raise ValueError("Cần 0 < advance <= size")
    last = ts - ts % advance
    first = max(0, last - size + advance)
    return [s for s in range(first, last + 1, advance) if s <= ts < s + size]


def _aggregate(pairs, size, key_field, value_field):
    acc: dict[tuple[int, str], list[float]] = defaultdict(lambda: [0, 0.0])
    for start, event in pairs:
        slot = acc[(start, event[key_field])]
        slot[0] += 1
        slot[1] += float(event[value_field])
    return [
        {
            "window_start": start,
            "window_end": start + size,
            "key": key,
            "count": count,
            "sum": round(total, 2),
        }
        for (start, key), (count, total) in sorted(acc.items())
    ]


def tumbling_aggregate(
    events: list[dict], size: int, key_field: str = "customer_state", value_field: str = "amount"
) -> list[dict]:
    pairs = ((tumbling_window_start(e["event_time"], size), e) for e in events)
    return _aggregate(pairs, size, key_field, value_field)


def hopping_aggregate(
    events: list[dict],
    size: int,
    advance: int,
    key_field: str = "customer_state",
    value_field: str = "amount",
) -> list[dict]:
    pairs = (
        (start, e) for e in events for start in hopping_window_starts(e["event_time"], size, advance)
    )
    return _aggregate(pairs, size, key_field, value_field)
