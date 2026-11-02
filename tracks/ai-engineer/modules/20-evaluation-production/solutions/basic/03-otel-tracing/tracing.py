"""Trace một pipeline RAG bằng OpenTelemetry SDK (lời giải)."""

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
    if not 0 <= sample_ratio <= 1:
        raise ValueError("sample_ratio phải trong [0, 1]")
    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name}),
        sampler=ParentBased(TraceIdRatioBased(sample_ratio)),
    )
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider


class JsonlSpanExporter(SpanExporter):
    def __init__(self, path):
        self.path = Path(path)

    def export(self, spans) -> SpanExportResult:
        with self.path.open("a", encoding="utf-8") as f:
            for span in spans:
                ctx = span.context
                f.write(json.dumps({
                    "name": span.name,
                    "trace_id": f"{ctx.trace_id:032x}",
                    "span_id": f"{ctx.span_id:016x}",
                    "parent_span_id": f"{span.parent.span_id:016x}" if span.parent else None,
                    "start_ns": span.start_time,
                    "end_ns": span.end_time,
                    "duration_ms": (span.end_time - span.start_time) / 1e6,
                    "status": span.status.status_code.name,
                    "service": span.resource.attributes.get("service.name"),
                    "attributes": {k: list(v) if isinstance(v, tuple) else v for k, v in span.attributes.items()},
                }, ensure_ascii=False) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


def traced_answer(question: str, retrieve, generate, tracer, prices: dict) -> str:
    with tracer.start_as_current_span("rag.request") as root:
        root.set_attribute("app.question", redact(question))
        with tracer.start_as_current_span("rag.retrieve") as span:
            docs = retrieve(question)
            span.set_attribute("rag.top_k", len(docs))
            span.set_attribute("rag.doc_ids", [str(d["id"]) for d in docs])
        with tracer.start_as_current_span("llm.chat") as span:
            out = generate(question, docs)
            cost = (out["input_tokens"] * prices["input"] + out["output_tokens"] * prices["output"]) / 1e6
            span.set_attribute("gen_ai.operation.name", "chat")
            span.set_attribute("gen_ai.request.model", out["model"])
            span.set_attribute("gen_ai.usage.input_tokens", out["input_tokens"])
            span.set_attribute("gen_ai.usage.output_tokens", out["output_tokens"])
            span.set_attribute("app.cost_usd", cost)
        root.set_attribute("app.cost_usd", cost)
        root.set_attribute("app.answer_chars", len(out["text"]))
        return out["text"]
