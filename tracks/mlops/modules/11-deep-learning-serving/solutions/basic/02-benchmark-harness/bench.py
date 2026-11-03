import time
from typing import Callable

import numpy as np


def summarize(latencies_ms: list[float], batch_size: int) -> dict:
    values = np.asarray(latencies_ms, dtype=float)
    return {
        "p50_ms": float(np.percentile(values, 50)),
        "p95_ms": float(np.percentile(values, 95)),
        "mean_ms": float(values.mean()),
        "throughput_ips": float(batch_size * len(values) / (values.sum() / 1000)),
    }


def benchmark(run: Callable[[np.ndarray], object], make_batch: Callable[[int], np.ndarray], batch_sizes: list[int],
              warmup: int = 5, iters: int = 30) -> list[dict]:
    results = []
    for batch_size in batch_sizes:
        batch = make_batch(batch_size)
        for _ in range(warmup):
            run(batch)
        latencies = []
        for _ in range(iters):
            started = time.perf_counter()
            run(batch)
            latencies.append((time.perf_counter() - started) * 1000)
        results.append({"batch_size": batch_size, "warmup": warmup, "iters": iters, "latencies_ms": latencies,
                        **summarize(latencies, batch_size)})
    return results
