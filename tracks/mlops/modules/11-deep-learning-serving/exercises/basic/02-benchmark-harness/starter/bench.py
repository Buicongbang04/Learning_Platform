import time
from typing import Callable

import numpy as np


def summarize(latencies_ms: list[float], batch_size: int) -> dict:
    # TODO: p50_ms, p95_ms (np.percentile), mean_ms, throughput_ips = batch_size * số lần / tổng giây
    raise NotImplementedError


def benchmark(run: Callable[[np.ndarray], object], make_batch: Callable[[int], np.ndarray], batch_sizes: list[int],
              warmup: int = 5, iters: int = 30) -> list[dict]:
    # TODO: mỗi batch size: tạo batch một lần, warmup không đo, rồi đo iters lần bằng time.perf_counter
    raise NotImplementedError
