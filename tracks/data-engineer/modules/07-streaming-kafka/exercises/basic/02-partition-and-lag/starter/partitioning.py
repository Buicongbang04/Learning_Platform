"""Mô phỏng partitioner, range assignor và consumer lag của Kafka bằng hàm thuần."""

from __future__ import annotations

import zlib  # noqa: F401  (bạn sẽ cần zlib.crc32)


def partition_for(key: bytes | None, num_partitions: int, counter: int = 0) -> int:
    """Chọn partition cho một record.

    - Có key: crc32(key) % num_partitions (Kafka thật dùng murmur2, ý tưởng giống hệt).
    - Không key: round-robin theo `counter`.
    """
    # TODO 1: num_partitions <= 0 thì raise ValueError; xử lý hai trường hợp có key / không key.
    raise NotImplementedError


def assign(events: list[dict], num_partitions: int) -> dict[int, list[dict]]:
    """Chia event vào partition theo key `order_id`, giữ thứ tự xuất hiện trong mỗi partition.

    Kết quả có đủ mọi partition từ 0 tới num_partitions - 1 (partition rỗng là list rỗng).
    Event không có order_id thì dùng round-robin, counter là số event không-key đã gặp.
    """
    # TODO 2
    raise NotImplementedError


def range_assign(partitions: list[int], consumers: list[str]) -> dict[str, list[int]]:
    """Range assignor: sắp consumer và partition, chia đều; `n % c` consumer đầu nhận thêm 1."""
    # TODO 3: consumers rỗng thì raise ValueError. Mỗi consumer nhận một dải partition liên tiếp.
    raise NotImplementedError


def consumer_lag(end_offsets: dict[int, int], committed: dict[int, int | None]) -> dict[int, int]:
    """Lag mỗi partition = end offset - committed offset (chưa commit thì tính từ 0). Không âm."""
    # TODO 4
    raise NotImplementedError


def total_lag(end_offsets: dict[int, int], committed: dict[int, int | None]) -> int:
    # TODO 5: tổng lag mọi partition.
    raise NotImplementedError
