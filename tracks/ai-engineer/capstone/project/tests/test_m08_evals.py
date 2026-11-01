"""M08: độ trễ có khoảng tin cậy, chi phí, kappa, cổng hồi quy, trace."""

import json
import math

import numpy as np
import pytest


def test_latency_summary(la):
    evals = la("evals")
    xs = [0.5, 1.0, 1.5, 2.0, 10.0]
    s = evals.latency_summary(xs)
    assert s["n"] == 5
    assert s["mean"] == pytest.approx(3.0)
    assert s["p50"] == pytest.approx(1.5)
    assert s["p95"] == pytest.approx(np.percentile(xs, 95))
    with pytest.raises(ValueError):
        evals.latency_summary([])


def test_percentile_ci(la):
    evals = la("evals")
    rng = np.random.default_rng(1)
    xs = list(rng.lognormal(0, 0.5, size=200))
    lo, hi = evals.percentile_ci(xs, 95, n_boot=500, seed=3)
    assert (lo, hi) == evals.percentile_ci(xs, 95, n_boot=500, seed=3)
    assert lo < np.percentile(xs, 95) < hi
    assert hi - lo < np.percentile(xs, 99) - np.percentile(xs, 50)
    narrow = evals.percentile_ci(xs, 95, n_boot=500, seed=3, level=0.5)
    assert lo <= narrow[0] <= narrow[1] <= hi
    assert evals.percentile_ci([2.0] * 10, 50, n_boot=50) == (2.0, 2.0)


def test_cost_per_query(la):
    evals = la("evals")
    assert evals.cost_per_query(2_000, 300, 1.0, 5.0) == pytest.approx(0.0035)
    assert evals.cost_per_query(0, 0, 3.0, 15.0) == 0.0


def test_cohen_kappa(la):
    evals = la("evals")
    judge = [True, True, True, False, False, True, False, True, True, False]
    human = [True, True, False, False, False, True, True, True, True, False]
    assert evals.cohen_kappa(judge, human) == pytest.approx((0.8 - 0.52) / 0.48)
    assert evals.cohen_kappa(judge, judge) == pytest.approx(1.0)
    assert math.isnan(evals.cohen_kappa([True, True], [True, True]))
    with pytest.raises(ValueError):
        evals.cohen_kappa([True], [True, False])
    with pytest.raises(ValueError):
        evals.cohen_kappa([], [])


def test_regression_gate(la):
    evals = la("evals")
    base = {"recall@10": 0.92, "refused": 0.20, "p95_s": 6.0}
    rules = {"recall@10": ("higher", 0.01), "refused": ("lower", 0.02), "p95_s": ("lower", 1.0)}
    assert evals.regression_gate({"recall@10": 0.915, "refused": 0.21, "p95_s": 6.9}, base, rules) == []
    fails = evals.regression_gate({"recall@10": 0.90, "refused": 0.25, "p95_s": 5.0}, base, rules)
    assert len(fails) == 2 and any("recall@10" in f for f in fails) and any("refused" in f for f in fails)
    assert len(evals.regression_gate({"recall@10": 0.99, "refused": 0.1}, base, rules)) == 1
    with pytest.raises(ValueError):
        evals.regression_gate(base, base, {"refused": ("down", 0.1)})


def test_tracer_nesting_errors_and_jsonl(la, tmp_path):
    tracing = la("tracing")
    tracer = tracing.Tracer()
    with tracer.span("request", user="u1"):
        with tracer.span("retrieve", k=5) as attrs:
            attrs["n_hits"] = 5
        with pytest.raises(KeyError):
            with tracer.span("llm"):
                raise KeyError("x")
    with tracer.span("request"):
        pass
    names = [s["name"] for s in tracer.spans]
    assert names == ["retrieve", "llm", "request", "request"]
    retrieve, llm, root, root2 = tracer.spans
    assert root["parent_id"] is None and retrieve["parent_id"] == root["span_id"] == llm["parent_id"]
    assert retrieve["trace_id"] == root["trace_id"] == llm["trace_id"] != root2["trace_id"]
    assert retrieve["attrs"] == {"k": 5, "n_hits": 5} and root["attrs"] == {"user": "u1"}
    assert llm["status"] == "error" and llm["error"] == "KeyError" and root["status"] == "ok"
    assert all(s["duration_s"] >= 0 for s in tracer.spans)
    assert root["duration_s"] >= retrieve["duration_s"]
    path = tmp_path / "trace.jsonl"
    tracer.write_jsonl(path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [r["name"] for r in rows] == names
