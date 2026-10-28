"""Dedup event theo event_id và mô phỏng log compaction của Kafka."""

from __future__ import annotations

from typing import Any


def dedup_events(events: list[dict]) -> list[dict]:
    """Giữ lần xuất hiện đầu tiên của mỗi event_id, giữ nguyên thứ tự.

    Event không có event_id thì giữ lại (không đủ thông tin để coi là trùng).
    """
    seen: set[str] = set()
    result = []
    for event in events:
        event_id = event.get("event_id")
        if event_id is None:
            result.append(event)
            continue
        if event_id in seen:
            continue
        seen.add(event_id)
        result.append(event)
    return result


def count_duplicates(events: list[dict]) -> dict[str, int]:
    """Số bản trùng (lần xuất hiện thứ 2 trở đi) theo event_id, chỉ những id có trùng."""
    counts: dict[str, int] = {}
    for event in events:
        event_id = event.get("event_id")
        if event_id is not None:
            counts[event_id] = counts.get(event_id, 0) + 1
    return {k: v - 1 for k, v in counts.items() if v > 1}


def compact(records: list[tuple[str, Any]]) -> dict[str, Any]:
    """Trạng thái cuối cùng sau compaction: giá trị mới nhất cho mỗi key, tombstone (None) xoá key."""
    state: dict[str, Any] = {}
    for key, value in records:
        if value is None:
            state.pop(key, None)
        else:
            state[key] = value
    return state


def compacted_offsets(records: list[tuple[str, Any]]) -> list[int]:
    """Offset (vị trí trong list) còn lại sau compaction: offset cuối cùng của mỗi key, tăng dần.

    Tombstone cũng được giữ (Kafka giữ tombstone thêm `delete.retention.ms` để consumer kịp thấy).
    """
    last: dict[str, int] = {}
    for offset, (key, _value) in enumerate(records):
        last[key] = offset
    return sorted(last.values())
