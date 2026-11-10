"""Máy tính capacity: từ benchmark một GPU và SLO độ trễ ra số GPU, chi phí self-host và điểm hoà vốn với API.

Một dòng benchmark (dict): {"concurrency": int, "ttft_p95_s": float, "tpot_p95_s": float}, đo ở prompt cố định.
Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

import math

HOURS_PER_MONTH = 730


def peak_rps(requests_per_day: float, peak_to_avg: float) -> float:
    """Request/giây giờ cao điểm: trung bình cả ngày (chia 86 400 giây) nhân hệ số cao điểm."""
    if requests_per_day < 0 or peak_to_avg < 1:
        raise ValueError("requests_per_day >= 0, peak_to_avg >= 1")
    return requests_per_day / 86_400 * peak_to_avg


def little_concurrency(rps: float, latency_s: float) -> float:
    """Định luật Little: số request đang xử lý trung bình L = lambda * W."""
    if rps < 0 or latency_s < 0:
        raise ValueError("rps, latency_s >= 0")
    return rps * latency_s


def request_latency(row: dict, output_tokens: int) -> float:
    """Độ trễ p95 xấp xỉ của một request ở điểm vận hành `row`: TTFT + output_tokens * TPOT."""
    if output_tokens < 0:
        raise ValueError("output_tokens >= 0")
    return row["ttft_p95_s"] + output_tokens * row["tpot_p95_s"]


def rps_per_gpu(row: dict, output_tokens: int) -> float:
    """Thông lượng (request/giây) một GPU giữ được ở điểm vận hành: concurrency / latency."""
    return row["concurrency"] / request_latency(row, output_tokens)


def best_operating_point(bench: list[dict], output_tokens: int, ttft_slo_s: float, e2e_slo_s: float) -> dict | None:
    """Dòng benchmark đạt cả hai SLO và có rps_per_gpu lớn nhất (bằng nhau: concurrency nhỏ hơn). None nếu không có."""
    ok = [
        r for r in bench
        if r["ttft_p95_s"] <= ttft_slo_s and request_latency(r, output_tokens) <= e2e_slo_s
    ]
    if not ok:
        return None
    return max(ok, key=lambda r: (rps_per_gpu(r, output_tokens), -r["concurrency"]))


def gpus_needed(
    peak_rps: float,
    bench: list[dict],
    output_tokens: int,
    ttft_slo_s: float,
    e2e_slo_s: float,
    headroom: float = 0.2,
    redundancy: int = 1,
) -> int:
    """Số GPU = ceil(peak_rps * (1 + headroom) / rps_per_gpu ở điểm vận hành tốt nhất) + redundancy."""
    if peak_rps < 0 or headroom < 0 or redundancy < 0:
        raise ValueError("peak_rps, headroom, redundancy >= 0")
    row = best_operating_point(bench, output_tokens, ttft_slo_s, e2e_slo_s)
    if row is None:
        raise ValueError("không điểm vận hành nào đạt SLO: cần GPU nhanh hơn, model nhỏ hơn hoặc nới SLO")
    return math.ceil(peak_rps * (1 + headroom) / rps_per_gpu(row, output_tokens) - 1e-9) + redundancy


def self_host_monthly_usd(n_gpus: int, usd_per_gpu_hour: float, hours_per_month: float = HOURS_PER_MONTH) -> float:
    """Chi phí thuê GPU chạy 24/7 một tháng (chưa gồm kỹ sư vận hành, lưu trữ, mạng)."""
    if n_gpus < 0 or usd_per_gpu_hour < 0:
        raise ValueError("n_gpus, usd_per_gpu_hour >= 0")
    return n_gpus * usd_per_gpu_hour * hours_per_month


def break_even_requests_per_month(
    fixed_monthly_usd: float, api_cost_per_request: float, self_host_cost_per_request: float = 0.0
) -> float:
    """Số request/tháng mà từ đó self-host rẻ hơn API. math.inf nếu API không đắt hơn phần biến đổi của self-host."""
    margin = api_cost_per_request - self_host_cost_per_request
    if margin <= 0:
        return math.inf
    return fixed_monthly_usd / margin
