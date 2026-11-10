"""M08: trace tối giản để học khái niệm; khi làm thật hãy nối OpenTelemetry như bài Basic 03 module 20.

Mỗi lần mở span gốc (không có span cha) là một trace mới.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path


class Tracer:
    def __init__(self):
        self.spans: list[dict] = []

    @contextmanager
    def span(self, name: str, **attrs):
        """Ghi một span vào `self.spans` khi span **kết thúc** (span con xong trước span cha).

        Mỗi span là dict có `trace_id`, `span_id`, `parent_id` (None với span gốc), `name`, `attrs` (dict, chính là
        đối tượng được `yield` để code bên trong thêm thuộc tính như số token), `status` (`"ok"` hoặc `"error"`),
        `duration_s`; khi lỗi có thêm `error` là tên lớp exception, và exception vẫn được ném tiếp.
        """
        raise NotImplementedError("M08: Tracer.span")
        yield {}

    def write_jsonl(self, path: Path) -> None:
        """Ghi nối mỗi span một dòng JSON (UTF-8, `ensure_ascii=False`)."""
        raise NotImplementedError("M08: Tracer.write_jsonl")
