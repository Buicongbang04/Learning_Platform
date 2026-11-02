import json
import math
import re

import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("service.ipynb")


def span(name, trace, sid, parent, ms, status="UNSET", **attrs):
    return {"name": name, "trace_id": f"{trace:032x}", "span_id": f"{sid:016x}",
            "parent_span_id": None if parent is None else f"{parent:016x}", "start_ns": 0,
            "end_ns": int(ms * 1e6), "duration_ms": ms, "status": status, "service": "zalo-rag", "attributes": attrs}


SPANS = [
    span("rag.request", 1, 1, None, 1000.0, **{"app.cost_usd": 0.002}),
    span("rag.retrieve", 1, 2, 1, 100.0),
    span("llm.chat", 1, 3, 1, 850.0),
    span("rag.request", 2, 4, None, 3000.0, **{"app.cost_usd": 0.004}),
    span("rag.retrieve", 2, 5, 4, 200.0),
    span("llm.chat", 2, 6, 4, 2700.0),
    span("rag.request", 3, 7, None, 500.0, status="ERROR"),
    span("rag.retrieve", 3, 8, 7, 120.0),
    span("llm.chat", 3, 9, 7, 300.0, status="ERROR"),
]


@pytest.fixture
def trace_file(tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in SPANS) + "\n", encoding="utf-8")
    return path


def test_load_spans(nb, trace_file):
    spans = nb.load_spans(trace_file)
    assert len(spans) == 9 and spans[0]["name"] == "rag.request" and spans[1]["parent_span_id"] == f"{1:016x}"


def test_span_table(nb, trace_file):
    df = nb.span_table(nb.load_spans(trace_file))
    assert list(df.columns) == nb.SPAN_COLUMNS == ["name", "count", "error_rate", "p50_ms", "p95_ms", "p99_ms",
                                                   "share_of_root"]
    assert list(df["name"]) == ["llm.chat", "rag.request", "rag.retrieve"]
    llm = df.set_index("name").loc["llm.chat"]
    assert llm["count"] == 3 and llm["error_rate"] == pytest.approx(1 / 3)
    assert llm["p50_ms"] == pytest.approx(850.0)
    assert llm["p95_ms"] == pytest.approx(np.percentile([850, 2700, 300], 95))
    assert llm["share_of_root"] == pytest.approx((850 + 2700 + 300) / 4500)
    root = df.set_index("name").loc["rag.request"]
    assert root["share_of_root"] == pytest.approx(1.0) and root["p99_ms"] == pytest.approx(np.percentile([1000, 3000, 500], 99))


def test_cost_and_slo(nb):
    assert nb.cost_per_1k(SPANS) == pytest.approx((0.002 + 0.004 + 0.0) / 3 * 1000), "span gốc thiếu chi phí tính 0"
    r = nb.root_slo(SPANS, threshold_ms=2000, target=0.9)
    assert r["n"] == 3 and r["good_ratio"] == pytest.approx(1 / 3), "request lỗi là xấu dù nhanh"
    assert r["burn_rate"] == pytest.approx((2 / 3) / 0.1) and not r["met"]
    assert nb.root_slo(SPANS, threshold_ms=3000, target=0.6)["met"]
    children = [s for s in SPANS if s["parent_span_id"] is not None]
    with pytest.raises(ValueError):
        nb.cost_per_1k(children)
    with pytest.raises(ValueError):
        nb.root_slo(children, 1000, 0.9)


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 600, "báo cáo: ít nhất 600 từ"
    assert len(re.findall(r"^\|.*\|\s*$", doc, re.M)) >= 6, "cần các bảng số liệu"
