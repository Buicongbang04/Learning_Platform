import time

import numpy as np
import pytest

import segkit
from testkit import Exercise

ex = Exercise(__file__)
KEYS = {"batch_size", "warmup", "iters", "latencies_ms", "p50_ms", "p95_ms", "mean_ms", "throughput_ips"}


def test_summarize_percentiles_and_throughput():
    bench = ex.module("bench.py")
    latencies = [10.0, 12.0, 11.0, 50.0, 13.0, 9.0, 10.0, 12.0, 11.0, 14.0]
    out = bench.summarize(latencies, batch_size=4)
    assert out["p50_ms"] == pytest.approx(np.percentile(latencies, 50))
    assert out["p95_ms"] == pytest.approx(np.percentile(latencies, 95))
    assert out["mean_ms"] == pytest.approx(np.mean(latencies))
    assert out["throughput_ips"] == pytest.approx(4 * 10 / (sum(latencies) / 1000))


class SlowStart:
    def __init__(self, slow_calls, slow_s=0.2, fast_s=0.002):
        self.slow_calls, self.slow_s, self.fast_s = slow_calls, slow_s, fast_s
        self.calls = {}

    def __call__(self, batch):
        n = self.calls.get(len(batch), 0)
        self.calls[len(batch)] = n + 1
        time.sleep(self.slow_s if n < self.slow_calls else self.fast_s)


def test_structure_order_and_call_counts():
    bench = ex.module("bench.py")
    run = SlowStart(slow_calls=0)
    made = []
    results = bench.benchmark(run, lambda b: made.append(b) or np.zeros((b, 3, 8, 8), np.float32), [1, 4, 2], warmup=2, iters=6)
    assert [r["batch_size"] for r in results] == [1, 4, 2]
    assert made == [1, 4, 2], "make_batch phải gọi đúng một lần cho mỗi batch size, ngoài vòng đo"
    for r in results:
        assert KEYS <= set(r)
        assert r["warmup"] == 2 and r["iters"] == 6
        assert len(r["latencies_ms"]) == 6
        assert r["p95_ms"] >= r["p50_ms"] > 0
    assert run.calls == {1: 8, 4: 8, 2: 8}


def test_warmup_calls_are_not_measured():
    bench = ex.module("bench.py")
    results = bench.benchmark(SlowStart(slow_calls=3), lambda b: np.zeros((b, 3, 8, 8), np.float32), [1, 2], warmup=3, iters=10)
    for r in results:
        assert max(r["latencies_ms"]) < 100, f"lần warmup chậm (200 ms) lọt vào số đo: {max(r['latencies_ms']):.0f} ms"
        assert r["p95_ms"] < 100


def test_batch_creation_is_outside_the_timed_loop():
    bench = ex.module("bench.py")

    def slow_make(b):
        time.sleep(0.2)
        return np.zeros((b, 3, 8, 8), np.float32)

    results = bench.benchmark(SlowStart(slow_calls=0), slow_make, [1], warmup=1, iters=5)
    assert results[0]["p50_ms"] < 100


def test_real_onnxruntime_session(tmp_path):
    bench = ex.module("bench.py")
    session = segkit.ort_session(segkit.export(segkit.tiny_model(), tmp_path / "seg.onnx"))
    rng = np.random.default_rng(0)
    results = bench.benchmark(lambda x: session.run(None, {"pixel_values": x}),
                              lambda b: rng.random((b, 3, 64, 64), dtype=np.float32), [1, 8], warmup=3, iters=15)
    assert [r["batch_size"] for r in results] == [1, 8]
    for r in results:
        assert r["p95_ms"] >= r["p50_ms"] > 0
        assert r["throughput_ips"] == pytest.approx(r["batch_size"] * 15 / (sum(r["latencies_ms"]) / 1000))
