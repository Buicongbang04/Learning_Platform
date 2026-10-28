"""Tumbling window theo event time, có watermark và xử lý event trễ."""

from __future__ import annotations


class TumblingWindowProcessor:
    """Aggregate count/total theo (tumbling window, key) và phát kết quả khi watermark vượt cuối window.

    - watermark = max_event_time đã thấy - allowed_lateness (None khi chưa có event).
    - Event thuộc window [s, s+size) là *late* nếu s + size <= watermark hiện tại (window đã đóng):
      không cộng vào kết quả, chỉ ghi vào `late_events`.
    - Sau khi nhận một event, mọi window có end <= watermark được phát ra (mỗi window đúng một lần).
    """

    def __init__(self, size: int, allowed_lateness: int = 0):
        if size <= 0 or allowed_lateness < 0:
            raise ValueError("size > 0 và allowed_lateness >= 0")
        self.size = size
        self.allowed_lateness = allowed_lateness
        self.max_event_time: int | None = None
        self.late_events: list[dict] = []
        self._state: dict[tuple[int, str], list] = {}

    @property
    def watermark(self) -> int | None:
        if self.max_event_time is None:
            return None
        return self.max_event_time - self.allowed_lateness

    def process(self, event: dict) -> list[dict]:
        ts = event["event_time"]
        start = ts - ts % self.size
        wm = self.watermark
        if wm is not None and start + self.size <= wm:
            self.late_events.append(event)
            return []
        slot = self._state.setdefault((start, event["key"]), [0, 0.0])
        slot[0] += 1
        slot[1] += float(event["amount"])
        if self.max_event_time is None or ts > self.max_event_time:
            self.max_event_time = ts
        return self._emit(lambda end: end <= self.watermark)

    def flush(self) -> list[dict]:
        """Kết thúc stream: phát mọi window còn lại."""
        return self._emit(lambda end: True)

    def _emit(self, ready) -> list[dict]:
        out = []
        for (start, key) in sorted(self._state):
            end = start + self.size
            if ready(end):
                count, total = self._state.pop((start, key))
                out.append(
                    {"window_start": start, "window_end": end, "key": key,
                     "count": count, "total": round(total, 2)}
                )
        return out


def run(events: list[dict], size: int, allowed_lateness: int) -> tuple[list[dict], list[dict]]:
    """Chạy cả stream qua processor, trả về (mọi kết quả đã phát kể cả flush, late events)."""
    processor = TumblingWindowProcessor(size, allowed_lateness)
    results: list[dict] = []
    for event in events:
        results.extend(processor.process(event))
    results.extend(processor.flush())
    return results, processor.late_events
