"""Dedup event theo event_id và mô phỏng log compaction của Kafka."""

from __future__ import annotations

from typing import Any


def dedup_events(events: list[dict]) -> list[dict]:
    """Giữ lần xuất hiện đầu tiên của mỗi event_id, giữ nguyên thứ tự.

    Event không có event_id thì giữ lại (không đủ thông tin để coi là trùng).
    """
    # TODO 1
    raise NotImplementedError


def count_duplicates(events: list[dict]) -> dict[str, int]:
    """Số bản trùng (lần xuất hiện thứ 2 trở đi) theo event_id, chỉ những id có trùng."""
    # TODO 2
    raise NotImplementedError


def compact(records: list[tuple[str, Any]]) -> dict[str, Any]:
    """Trạng thái cuối cùng sau compaction: giá trị mới nhất cho mỗi key, tombstone (None) xoá key."""
    # TODO 3
    raise NotImplementedError


def compacted_offsets(records: list[tuple[str, Any]]) -> list[int]:
    """Offset (vị trí trong list) còn lại sau compaction: offset cuối cùng của mỗi key, tăng dần.

    Tombstone cũng được giữ (Kafka giữ tombstone thêm `delete.retention.ms` để consumer kịp thấy).
    """
    # TODO 4
    raise NotImplementedError
