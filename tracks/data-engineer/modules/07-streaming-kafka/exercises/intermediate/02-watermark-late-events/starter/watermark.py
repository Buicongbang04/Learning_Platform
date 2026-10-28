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
        # state: (window_start, key) -> [count, total]
        self._state: dict[tuple[int, str], list] = {}

    @property
    def watermark(self) -> int | None:
        # TODO 1: None nếu chưa thấy event, ngược lại max_event_time - allowed_lateness.
        raise NotImplementedError

    def process(self, event: dict) -> list[dict]:
        """Nhận một event {"event_time", "key", "amount"}; trả về các window vừa đóng.

        Mỗi kết quả: {"window_start", "window_end", "key", "count", "total"} (total làm tròn 2 chữ số),
        sắp theo (window_start, key).
        """
        # TODO 2: kiểm tra late theo watermark *trước khi* cập nhật max_event_time.
        # TODO 3: cộng vào state, cập nhật max_event_time, phát các window có end <= watermark.
        raise NotImplementedError

    def flush(self) -> list[dict]:
        """Kết thúc stream: phát mọi window còn lại."""
        # TODO 4
        raise NotImplementedError


def run(events: list[dict], size: int, allowed_lateness: int) -> tuple[list[dict], list[dict]]:
    """Chạy cả stream qua processor, trả về (mọi kết quả đã phát kể cả flush, late events)."""
    # TODO 5
    raise NotImplementedError
