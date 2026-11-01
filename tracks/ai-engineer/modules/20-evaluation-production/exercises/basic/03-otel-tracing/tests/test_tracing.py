import json
import random

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from testkit import Exercise

ex = Exercise(__file__)

PRICES = {"input": 0.10, "output": 0.50}
DOCS = [{"id": "100/2019/nđ-cp+21", "text": "..."}, {"id": "100/2019/nđ-cp+74", "text": "..."}]


@pytest.fixture(scope="module")
def tr():
    return ex.module("tracing.py")


def retrieve(question):
    return DOCS


def generate(question, docs):
    return {"text": "Phạt từ 800 000 tới 1 000 000 đồng [1].", "model": "qwen2.5:3b",
            "input_tokens": 1200, "output_tokens": 80}


def run_one(tr, sample_ratio=1.0, question="Không mang bằng lái bị phạt bao nhiêu?"):
    exporter = InMemorySpanExporter()
    provider = tr.make_provider(exporter, sample_ratio=sample_ratio)
    tracer = provider.get_tracer("test")
    answer = tr.traced_answer(question, retrieve, generate, tracer, PRICES)
    return answer, exporter.get_finished_spans(), provider


def by_name(spans):
    return {s.name: s for s in spans}


def test_span_tree(tr):
    answer, spans, _ = run_one(tr)
    assert answer.startswith("Phạt từ")
    names = by_name(spans)
    assert set(names) == {"rag.request", "rag.retrieve", "llm.chat"}, [s.name for s in spans]
    root, ret, llm = names["rag.request"], names["rag.retrieve"], names["llm.chat"]
    assert root.parent is None, "rag.request là span gốc"
    assert ret.parent.span_id == root.context.span_id and llm.parent.span_id == root.context.span_id
    assert len({s.context.trace_id for s in spans}) == 1, "ba span cùng một trace"
    assert ret.start_time <= ret.end_time <= llm.start_time, "retrieve xong rồi mới gọi LLM"
    assert root.start_time <= ret.start_time and llm.end_time <= root.end_time


def test_attributes(tr):
    _, spans, _ = run_one(tr)
    names = by_name(spans)
    llm, ret, root = names["llm.chat"], names["rag.retrieve"], names["rag.request"]
    assert llm.attributes["gen_ai.operation.name"] == "chat"
    assert llm.attributes["gen_ai.request.model"] == "qwen2.5:3b"
    assert llm.attributes["gen_ai.usage.input_tokens"] == 1200
    assert llm.attributes["gen_ai.usage.output_tokens"] == 80
    cost = (1200 * 0.10 + 80 * 0.50) / 1e6
    assert llm.attributes["app.cost_usd"] == pytest.approx(cost)
    assert root.attributes["app.cost_usd"] == pytest.approx(cost)
    assert ret.attributes["rag.top_k"] == 2
    assert list(ret.attributes["rag.doc_ids"]) == ["100/2019/nđ-cp+21", "100/2019/nđ-cp+74"]
    assert root.resource.attributes["service.name"] == "zalo-rag"


def test_question_is_redacted(tr):
    q = "Tôi là an.nguyen@example.com, số 0912345678, không mang bằng lái bị phạt bao nhiêu?"
    _, spans, _ = run_one(tr, question=q)
    stored = by_name(spans)["rag.request"].attributes["app.question"]
    assert "an.nguyen@example.com" not in stored and "0912345678" not in stored
    assert "[EMAIL]" in stored and "[PHONE]" in stored and "bằng lái" in stored
    dumped = json.dumps([dict(s.attributes) for s in spans], ensure_ascii=False)
    assert "0912345678" not in dumped, "không span nào được chứa PII thô"


def test_errors_are_recorded_and_raised(tr):
    exporter = InMemorySpanExporter()
    tracer = tr.make_provider(exporter).get_tracer("test")

    def broken(question, docs):
        raise TimeoutError("LLM quá thời gian chờ")

    with pytest.raises(TimeoutError):
        tr.traced_answer("câu hỏi", retrieve, broken, tracer, PRICES)
    names = by_name(exporter.get_finished_spans())
    assert names["llm.chat"].status.status_code == StatusCode.ERROR
    assert names["rag.request"].status.status_code == StatusCode.ERROR
    assert names["rag.retrieve"].status.status_code != StatusCode.ERROR
    assert any(e.name == "exception" for e in names["llm.chat"].events), "ghi exception thành event của span"


def test_sampling_is_per_trace(tr):
    exporter = InMemorySpanExporter()
    tracer = tr.make_provider(exporter, sample_ratio=0.3).get_tracer("test")
    random.seed(0)
    for i in range(400):
        tr.traced_answer(f"câu {i}", retrieve, generate, tracer, PRICES)
    spans = exporter.get_finished_spans()
    traces = {}
    for s in spans:
        traces.setdefault(s.context.trace_id, []).append(s.name)
    assert all(sorted(v) == ["llm.chat", "rag.request", "rag.retrieve"] for v in traces.values()), \
        "lấy mẫu theo cả trace: span con đi theo quyết định của span gốc"
    assert 0.22 <= len(traces) / 400 <= 0.38


def test_sampling_extremes_and_bad_ratio(tr):
    assert run_one(tr, sample_ratio=0.0)[1] == ()
    assert len(run_one(tr, sample_ratio=1.0)[1]) == 3
    with pytest.raises(ValueError):
        tr.make_provider(InMemorySpanExporter(), sample_ratio=1.5)


def test_jsonl_exporter(tr, tmp_path):
    path = tmp_path / "spans.jsonl"
    provider = tr.make_provider(tr.JsonlSpanExporter(path), service_name="svc-test")
    tracer = provider.get_tracer("test")
    tr.traced_answer("câu một", retrieve, generate, tracer, PRICES)
    tr.traced_answer("câu hai", retrieve, generate, tracer, PRICES)
    provider.shutdown()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 6
    keys = {"name", "trace_id", "span_id", "parent_span_id", "start_ns", "end_ns", "duration_ms", "status",
            "service", "attributes"}
    assert all(set(r) == keys for r in rows)
    roots = [r for r in rows if r["name"] == "rag.request"]
    assert len(roots) == 2 and all(r["parent_span_id"] is None for r in roots)
    for r in rows:
        assert len(r["trace_id"]) == 32 and len(r["span_id"]) == 16 and int(r["trace_id"], 16) > 0
        assert r["service"] == "svc-test" and r["status"] in {"UNSET", "OK", "ERROR"}
        assert r["duration_ms"] == pytest.approx((r["end_ns"] - r["start_ns"]) / 1e6)
        if r["name"] != "rag.request":
            parent = next(p for p in roots if p["trace_id"] == r["trace_id"])
            assert r["parent_span_id"] == parent["span_id"]
    llm = next(r for r in rows if r["name"] == "llm.chat")
    assert llm["attributes"]["gen_ai.usage.output_tokens"] == 80
    ret = next(r for r in rows if r["name"] == "rag.retrieve")
    assert ret["attributes"]["rag.doc_ids"] == ["100/2019/nđ-cp+21", "100/2019/nđ-cp+74"]
