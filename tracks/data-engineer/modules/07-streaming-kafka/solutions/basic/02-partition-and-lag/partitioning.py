"""Mô phỏng partitioner, range assignor và consumer lag của Kafka bằng hàm thuần."""

from __future__ import annotations

import zlib


def partition_for(key: bytes | None, num_partitions: int, counter: int = 0) -> int:
    """Chọn partition cho một record.

    - Có key: crc32(key) % num_partitions (Kafka thật dùng murmur2, ý tưởng giống hệt).
    - Không key: round-robin theo `counter`.
    """
    if num_partitions <= 0:
        raise ValueError("num_partitions phải > 0")
    if key is None:
        return counter % num_partitions
    return zlib.crc32(key) % num_partitions


def assign(events: list[dict], num_partitions: int) -> dict[int, list[dict]]:
    """Chia event vào partition theo key `order_id`, giữ thứ tự xuất hiện trong mỗi partition.

    Kết quả có đủ mọi partition từ 0 tới num_partitions - 1 (partition rỗng là list rỗng).
    Event không có order_id thì dùng round-robin, counter là số event không-key đã gặp.
    """
    result: dict[int, list[dict]] = {p: [] for p in range(num_partitions)}
    keyless = 0
    for event in events:
        order_id = event.get("order_id")
        if order_id:
            p = partition_for(str(order_id).encode("utf-8"), num_partitions)
        else:
            p = partition_for(None, num_partitions, keyless)
            keyless += 1
        result[p].append(event)
    return result


def range_assign(partitions: list[int], consumers: list[str]) -> dict[str, list[int]]:
    """Range assignor: sắp consumer và partition, chia đều; `n % c` consumer đầu nhận thêm 1."""
    if not consumers:
        raise ValueError("Cần ít nhất một consumer")
    parts = sorted(partitions)
    members = sorted(consumers)
    per, extra = divmod(len(parts), len(members))
    result: dict[str, list[int]] = {}
    start = 0
    for i, member in enumerate(members):
        size = per + (1 if i < extra else 0)
        result[member] = parts[start : start + size]
        start += size
    return result


def consumer_lag(end_offsets: dict[int, int], committed: dict[int, int | None]) -> dict[int, int]:
    """Lag mỗi partition = end offset - committed offset (chưa commit thì tính từ 0). Không âm."""
    lags = {}
    for partition, end in end_offsets.items():
        done = committed.get(partition) or 0
        lags[partition] = max(end - done, 0)
    return lags


def total_lag(end_offsets: dict[int, int], committed: dict[int, int | None]) -> int:
    return sum(consumer_lag(end_offsets, committed).values())
