"""Ngân sách độ trễ của một request LLM: TTFT, end-to-end, trần tốc độ decode, percentile qua nhiều bước.

Quy ước (README bài): TTFT = overhead + prompt_tokens / prefill_tok_s; E2E = TTFT + output_tokens / decode_tok_s.
Percentile theo nội suy tuyến tính giữa hai phần tử kề nhau (mặc định của numpy.percentile).
Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

import math


def ttft(prompt_tokens: int, prefill_tok_s: float, overhead_s: float = 0.0) -> float:
    """Time to first token (giây)."""
    # TODO
    raise NotImplementedError


def e2e_latency(
    prompt_tokens: int, output_tokens: int, prefill_tok_s: float, decode_tok_s: float, overhead_s: float = 0.0
) -> float:
    """Độ trễ end-to-end (giây) khi sinh `output_tokens` token."""
    # TODO
    raise NotImplementedError


def decode_upper_bound_tok_s(bytes_per_token: float, bandwidth_bytes_s: float) -> float:
    """Trần tốc độ decode batch 1: mỗi token phải đọc `bytes_per_token` byte từ bộ nhớ GPU."""
    # TODO
    raise NotImplementedError


def percentile(samples: list[float], q: float) -> float:
    """Percentile q (0..100) theo nội suy tuyến tính, khớp numpy.percentile mặc định."""
    # TODO
    raise NotImplementedError


def pipeline_percentiles(stage_samples: dict[str, list[float]], q: float) -> tuple[float, float]:
    """Pipeline tuần tự: các bước chạy nối tiếp, `stage_samples[s][i]` là thời gian bước s của request i.

    Trả (percentile q của tổng thời gian từng request, tổng các percentile q của từng bước).
    """
    # TODO
    raise NotImplementedError


def max_output_tokens(
    budget_s: float, prompt_tokens: int, prefill_tok_s: float, decode_tok_s: float, overhead_s: float = 0.0
) -> int:
    """Số token output tối đa để E2E không vượt `budget_s`. 0 nếu TTFT đã vượt ngân sách."""
    # TODO
    raise NotImplementedError
