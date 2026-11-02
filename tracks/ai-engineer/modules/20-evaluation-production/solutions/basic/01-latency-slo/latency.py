"""Số đo độ trễ, chi phí và SLO của một dịch vụ LLM (lời giải)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Request:
    t_arrival: float
    t_start: float
    token_times: list[float] = field(default_factory=list)
    ok: bool = True


def breakdown(req: Request) -> dict:
    times = list(req.token_times)
    if not times:
        raise ValueError("request không có token nào")
    if req.t_start < req.t_arrival or times[0] < req.t_start:
        raise ValueError("thời điểm không theo thứ tự arrival <= start <= token đầu")
    if any(b < a for a, b in zip(times, times[1:])):
        raise ValueError("token_times phải không giảm")
    itl = [b - a for a, b in zip(times, times[1:])]
    return {
        "queue_s": req.t_start - req.t_arrival,
        "ttft_s": times[0] - req.t_arrival,
        "service_ttft_s": times[0] - req.t_start,
        "e2e_s": times[-1] - req.t_arrival,
        "tpot_s": (times[-1] - times[0]) / (len(times) - 1) if len(times) > 1 else 0.0,
        "itl_s": itl,
        "n_tokens": len(times),
    }


def bootstrap_percentile_ci(samples, q: float, n_boot: int = 2000, seed: int = 0,
                            level: float = 0.95) -> tuple[float, float, float]:
    x = np.asarray(samples, dtype=float)
    if x.ndim != 1 or len(x) < 2:
        raise ValueError("cần ít nhất 2 mẫu")
    if not 0 <= q <= 100 or not 0 < level < 1:
        raise ValueError("q phải trong [0, 100], level trong (0, 1)")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    stats = np.percentile(x[idx], q, axis=1)
    tail = (1 - level) / 2 * 100
    lo, hi = np.percentile(stats, [tail, 100 - tail])
    return float(np.percentile(x, q)), float(lo), float(hi)


def histogram_quantile(bounds, cumulative_counts, q: float) -> float:
    bounds = [float(b) for b in bounds]
    counts = [float(c) for c in cumulative_counts]
    if len(bounds) != len(counts) or not bounds:
        raise ValueError("bounds và cumulative_counts phải cùng độ dài, không rỗng")
    if any(b <= a for a, b in zip(bounds, bounds[1:])) or any(b < a for a, b in zip(counts, counts[1:])):
        raise ValueError("bounds phải tăng hẳn, cumulative_counts không giảm")
    if not 0 <= q <= 1:
        raise ValueError("q phải trong [0, 1]")
    total = counts[-1]
    if total == 0:
        return math.nan
    rank = q * total
    for i, (upper, cum) in enumerate(zip(bounds, counts)):
        if cum >= rank:
            if math.isinf(upper):
                return bounds[i - 1] if i > 0 else math.nan
            lower = bounds[i - 1] if i > 0 else 0.0
            prev = counts[i - 1] if i > 0 else 0.0
            if cum == prev:
                return upper
            return lower + (upper - lower) * (rank - prev) / (cum - prev)
    return bounds[-1]


def cost_per_1k(usages: list[dict], prices: dict) -> float:
    if not usages:
        raise ValueError("không có request nào")
    total = 0.0
    for u in usages:
        n_in, n_out = u["input_tokens"], u["output_tokens"]
        cached = u.get("cached_tokens", 0)
        if min(n_in, n_out, cached) < 0 or cached > n_in:
            raise ValueError(f"usage không hợp lệ: {u}")
        total += (n_in - cached) * prices["input"] + cached * prices["cached_input"] + n_out * prices["output"]
    return total / 1e6 / len(usages) * 1000


def slo_report(latencies, ok, threshold_s: float, target: float) -> dict:
    lat = np.asarray(latencies, dtype=float)
    good_ok = np.asarray(ok, dtype=bool)
    if len(lat) == 0 or len(lat) != len(good_ok):
        raise ValueError("latencies và ok phải cùng độ dài, không rỗng")
    if not 0 < target < 1:
        raise ValueError("target phải trong (0, 1)")
    good = good_ok & (lat <= threshold_s)
    good_ratio = float(good.mean())
    budget = 1 - target
    return {
        "n": int(len(lat)),
        "good_ratio": good_ratio,
        "bad": int((~good).sum()),
        "error_budget": budget,
        "burn_rate": (1 - good_ratio) / budget,
        "met": good_ratio >= target,
    }
