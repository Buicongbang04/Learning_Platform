import json

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Hai response thật của Ollama 0.13.5 với qwen2.5:3b trên laptop của track (2026-10-30), bỏ trường `message`:
# lần gọi đầu (model chưa nạp: cold start) và lần gọi ngay sau đó.
COLD = {"model": "qwen2.5:3b", "done": True, "done_reason": "length", "total_duration": 5826663552,
        "load_duration": 4832526813, "prompt_eval_count": 41, "prompt_eval_duration": 28386309,
        "eval_count": 64, "eval_duration": 873148879}
WARM = {"model": "qwen2.5:3b", "done": True, "done_reason": "length", "total_duration": 1149522239,
        "load_duration": 187046486, "prompt_eval_count": 41, "prompt_eval_duration": 12412302,
        "eval_count": 64, "eval_duration": 864244773}


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("latency.ipynb")


# ---------- ollama_metrics ----------


def test_metrics_real_warm(nb):
    m = nb.ollama_metrics(WARM)
    assert (m["n_in"], m["n_out"]) == (41, 64)
    assert isinstance(m["n_in"], int) and isinstance(m["n_out"], int)
    assert m["load_s"] == pytest.approx(0.187046486)
    assert m["prefill_s"] == pytest.approx(0.012412302)
    assert m["decode_s"] == pytest.approx(0.864244773)
    assert m["total_s"] == pytest.approx(1.149522239)
    assert m["prefill_tps"] == pytest.approx(41 / 0.012412302)  # khoảng 3 303 token/giây
    assert m["decode_tps"] == pytest.approx(64 / 0.864244773)  # khoảng 74 token/giây
    assert m["ttft_s"] == pytest.approx(0.187046486 + 0.012412302)


def test_metrics_cold_start(nb):
    m = nb.ollama_metrics(COLD)
    assert m["load_s"] == pytest.approx(4.832526813)
    assert m["ttft_s"] > 4.8  # cold start chiếm gần hết TTFT


def test_metrics_missing_fields_and_zero_duration(nb):
    m = nb.ollama_metrics({"prompt_eval_count": 10, "prompt_eval_duration": 0, "eval_count": 0,
                           "eval_duration": 0, "total_duration": 1_000_000})
    assert m["load_s"] == 0.0 and m["ttft_s"] == 0.0
    assert m["prefill_tps"] == 0.0 and m["decode_tps"] == 0.0
    assert m["total_s"] == pytest.approx(0.001)
    assert nb.ollama_metrics({})["n_out"] == 0


# ---------- summarize ----------


def test_summarize(nb):
    s = nb.summarize([1.0, 2.0, 3.0, 4.0, 10.0])
    assert s["n"] == 5
    assert s["mean"] == pytest.approx(4.0)
    assert s["p50"] == pytest.approx(3.0)
    assert s["p95"] == pytest.approx(8.8)  # nội suy tuyến tính giữa 4 và 10
    assert s["max"] == pytest.approx(10.0)


def test_summarize_tail(nb):
    # 95 request nhanh, 5 request rất chậm: trung bình bị kéo lên, p50 không thấy đuôi, p95 thấy
    values = [1.0] * 95 + [20.0] * 5
    s = nb.summarize(values)
    assert s["p50"] == pytest.approx(1.0)
    assert s["mean"] == pytest.approx(1.95)
    assert s["p95"] == pytest.approx(1.95)
    assert nb.summarize(np.array([2.5]))["p95"] == pytest.approx(2.5)
    with pytest.raises(ValueError):
        nb.summarize([])


# ---------- fit_latency, predict_latency ----------


def test_fit_exact_linear(nb):
    n_in = [100, 500, 1000, 2000, 300, 300, 300]
    n_out = [64, 64, 64, 64, 16, 128, 256]
    total = [0.3 + 0.0004 * a + 0.015 * b for a, b in zip(n_in, n_out)]
    m = nb.fit_latency(n_in, n_out, total)
    assert m["a"] == pytest.approx(0.3, abs=1e-9)
    assert m["b"] == pytest.approx(0.0004, abs=1e-12)
    assert m["c"] == pytest.approx(0.015, abs=1e-11)
    assert m["r2"] == pytest.approx(1.0, abs=1e-12)
    assert nb.predict_latency(m, 2000, 300) == pytest.approx(0.3 + 0.8 + 4.5)


def test_fit_noisy_matches_lstsq(nb):
    rng = np.random.default_rng(0)
    n_in = rng.integers(50, 3000, 30)
    n_out = rng.integers(8, 300, 30)
    total = 0.2 + 0.0015 * n_in + 0.09 * n_out + rng.normal(0, 0.3, 30)
    m = nb.fit_latency(list(n_in), list(n_out), list(total))
    X = np.column_stack([np.ones(30), n_in, n_out])
    ref, *_ = np.linalg.lstsq(X, total, rcond=None)
    assert [m["a"], m["b"], m["c"]] == pytest.approx(list(ref), rel=1e-9, abs=1e-12)
    resid = total - X @ ref
    assert m["r2"] == pytest.approx(1 - (resid ** 2).sum() / ((total - total.mean()) ** 2).sum(), abs=1e-12)
    assert 0.9 < m["r2"] < 1.0
    assert all(isinstance(m[k], float) for k in ["a", "b", "c", "r2"])


def test_fit_errors(nb):
    with pytest.raises(ValueError):
        nb.fit_latency([1, 2], [1, 2], [1.0, 2.0])
    with pytest.raises(ValueError):
        nb.fit_latency([1, 2, 3], [1, 2], [1.0, 2.0, 3.0])


# ---------- stream_timing ----------


def test_stream_timing(nb):
    t = nb.stream_timing(100.0, [100.25, 100.30, 100.35, 100.45])
    assert t["ttft_s"] == pytest.approx(0.25)
    assert t["e2e_s"] == pytest.approx(0.45)
    assert t["tpot_s"] == pytest.approx(0.20 / 3)


def test_stream_timing_single_chunk_and_empty(nb):
    t = nb.stream_timing(5.0, [5.5])
    assert t == pytest.approx({"ttft_s": 0.5, "e2e_s": 0.5, "tpot_s": 0.0})
    with pytest.raises(ValueError):
        nb.stream_timing(5.0, [])


def test_metrics_json_roundtrip(nb):
    # response đọc từ JSON (số nguyên lớn) cho cùng kết quả
    m = nb.ollama_metrics(json.loads(json.dumps(WARM)))
    assert m["decode_tps"] == pytest.approx(74.05, abs=0.01)
