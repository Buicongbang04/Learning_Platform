"""Số đo độ trễ, chi phí và SLO của một dịch vụ LLM.

Đọc đề trong README của bài. Chỉ dùng thư viện chuẩn và numpy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Request:
    """Một request đo phía client. Mọi thời điểm tính bằng giây trên cùng một đồng hồ."""

    t_arrival: float
    t_start: float
    token_times: list[float] = field(default_factory=list)
    ok: bool = True


def breakdown(req: Request) -> dict:
    """queue_s, ttft_s, service_ttft_s, e2e_s, tpot_s, itl_s, n_tokens của một request."""
    # TODO
    raise NotImplementedError


def bootstrap_percentile_ci(samples, q: float, n_boot: int = 2000, seed: int = 0,
                            level: float = 0.95) -> tuple[float, float, float]:
    """(percentile q của mẫu, cận dưới, cận trên) bằng bootstrap phân vị."""
    # TODO
    raise NotImplementedError


def histogram_quantile(bounds, cumulative_counts, q: float) -> float:
    """Ước lượng phân vị q (0..1) từ histogram tích luỹ kiểu Prometheus."""
    # TODO
    raise NotImplementedError


def cost_per_1k(usages: list[dict], prices: dict) -> float:
    """Chi phí USD cho 1 000 request, giá tính theo triệu token."""
    # TODO
    raise NotImplementedError


def slo_report(latencies, ok, threshold_s: float, target: float) -> dict:
    """n, good_ratio, bad, error_budget, burn_rate, met."""
    # TODO
    raise NotImplementedError
