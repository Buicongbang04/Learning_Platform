"""Tumbling và hopping window aggregation theo event time (giây epoch)."""

from __future__ import annotations


def tumbling_window_start(ts: int, size: int) -> int:
    # TODO 1: điểm bắt đầu tumbling window chứa ts. size <= 0 thì raise ValueError.
    raise NotImplementedError


def hopping_window_starts(ts: int, size: int, advance: int) -> list[int]:
    """Mọi window [s, s+size) chứa ts, với s chia hết cho advance và s >= 0. Tăng dần."""
    # TODO 2: kiểm tra 0 < advance <= size (sai thì ValueError), rồi liệt kê các s.
    raise NotImplementedError


def tumbling_aggregate(
    events: list[dict], size: int, key_field: str = "customer_state", value_field: str = "amount"
) -> list[dict]:
    """Gom event theo (tumbling window, key).

    Mỗi phần tử kết quả: {"window_start", "window_end", "key", "count", "sum"}; sum làm tròn 2 chữ số.
    Sắp theo (window_start, key).
    """
    # TODO 3
    raise NotImplementedError


def hopping_aggregate(
    events: list[dict],
    size: int,
    advance: int,
    key_field: str = "customer_state",
    value_field: str = "amount",
) -> list[dict]:
    """Như tumbling_aggregate nhưng mỗi event được cộng vào mọi hopping window chứa nó."""
    # TODO 4
    raise NotImplementedError
