"""Ngân sách độ trễ của một request LLM: TTFT, end-to-end, trần tốc độ decode, percentile qua nhiều bước.

Quy ước (README bài): TTFT = overhead + prompt_tokens / prefill_tok_s; E2E = TTFT + output_tokens / decode_tok_s.
Percentile theo nội suy tuyến tính giữa hai phần tử kề nhau (mặc định của numpy.percentile).
Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

import math


def ttft(prompt_tokens: int, prefill_tok_s: float, overhead_s: float = 0.0) -> float:
    """Time to first token (giây)."""
    if prompt_tokens < 0 or prefill_tok_s <= 0 or overhead_s < 0:
        raise ValueError("prompt_tokens >= 0, prefill_tok_s > 0, overhead_s >= 0")
    return overhead_s + prompt_tokens / prefill_tok_s


def e2e_latency(
    prompt_tokens: int, output_tokens: int, prefill_tok_s: float, decode_tok_s: float, overhead_s: float = 0.0
) -> float:
    """Độ trễ end-to-end (giây) khi sinh `output_tokens` token."""
    if output_tokens < 0 or decode_tok_s <= 0:
        raise ValueError("output_tokens >= 0, decode_tok_s > 0")
    return ttft(prompt_tokens, prefill_tok_s, overhead_s) + output_tokens / decode_tok_s


def decode_upper_bound_tok_s(bytes_per_token: float, bandwidth_bytes_s: float) -> float:
    """Trần tốc độ decode batch 1: mỗi token phải đọc `bytes_per_token` byte từ bộ nhớ GPU."""
    if bytes_per_token <= 0 or bandwidth_bytes_s <= 0:
        raise ValueError("bytes_per_token > 0, bandwidth_bytes_s > 0")
    return bandwidth_bytes_s / bytes_per_token


def percentile(samples: list[float], q: float) -> float:
    """Percentile q (0..100) theo nội suy tuyến tính, khớp numpy.percentile mặc định."""
    if not samples:
        raise ValueError("samples rỗng")
    if not 0 <= q <= 100:
        raise ValueError("q trong [0, 100]")
    xs = sorted(samples)
    pos = (len(xs) - 1) * q / 100
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return float(xs[lo] + (xs[hi] - xs[lo]) * (pos - lo))


def pipeline_percentiles(stage_samples: dict[str, list[float]], q: float) -> tuple[float, float]:
    """Pipeline tuần tự: các bước chạy nối tiếp, `stage_samples[s][i]` là thời gian bước s của request i.

    Trả (percentile q của tổng thời gian từng request, tổng các percentile q của từng bước).
    """
    if not stage_samples:
        raise ValueError("cần ít nhất một bước")
    lengths = {len(v) for v in stage_samples.values()}
    if len(lengths) != 1:
        raise ValueError("mọi bước phải có cùng số request")
    totals = [sum(vals) for vals in zip(*stage_samples.values())]
    return percentile(totals, q), sum(percentile(v, q) for v in stage_samples.values())


def max_output_tokens(
    budget_s: float, prompt_tokens: int, prefill_tok_s: float, decode_tok_s: float, overhead_s: float = 0.0
) -> int:
    """Số token output tối đa để E2E không vượt `budget_s`. 0 nếu TTFT đã vượt ngân sách."""
    remaining = budget_s - ttft(prompt_tokens, prefill_tok_s, overhead_s)
    if remaining <= 0:
        return 0
    return int(math.floor(remaining * decode_tok_s + 1e-9))
