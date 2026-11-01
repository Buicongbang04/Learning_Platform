"""Trace một pipeline RAG bằng OpenTelemetry SDK.

Đọc đề trong README của bài. `redact` đã viết sẵn (module 19 dạy che PII kỹ hơn).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<!\d)(?:\+84|0)\d{9}(?!\d)")


def redact(text: str) -> str:
    return PHONE.sub("[PHONE]", EMAIL.sub("[EMAIL]", text))


def make_provider(exporter: SpanExporter, sample_ratio: float = 1.0,
                  service_name: str = "zalo-rag") -> TracerProvider:
    """TracerProvider riêng (không đặt làm provider toàn cục), lấy mẫu theo trace, xuất span qua exporter."""
    # TODO
    raise NotImplementedError


class JsonlSpanExporter(SpanExporter):
    """Ghi mỗi span đã kết thúc thành một dòng JSON."""

    def __init__(self, path):
        self.path = Path(path)

    def export(self, spans) -> SpanExportResult:
        # TODO
        raise NotImplementedError

    def shutdown(self) -> None:
        pass


def traced_answer(question: str, retrieve, generate, tracer, prices: dict) -> str:
    """Trả lời một câu hỏi qua retrieve rồi generate, mỗi bước một span con của span gốc."""
    # TODO
    raise NotImplementedError
