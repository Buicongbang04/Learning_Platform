"""Ước lượng chi phí inference: một request, một tháng, tự host, và chọn model theo ràng buộc.

Giá tính bằng USD cho mỗi triệu token (USD/MTok). Một bảng giá là dict:

    {
        "input": 2.0,            # bắt buộc
        "output": 10.0,          # bắt buộc
        "cached_input": 0.2,     # tuỳ chọn; thiếu thì token cache tính giá "input"
        "long_context": {        # tuỳ chọn: prompt VƯỢT ngưỡng thì cả request tính theo bảng giá con
            "threshold": 100_000,
            "input": 4.0, "output": 15.0, "cached_input": 0.4,
        },
    }

Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

MTOK = 1_000_000


def _tier(price: dict, n_in: float) -> dict:
    long = price.get("long_context")
    if long is not None and n_in > long["threshold"]:
        return long
    return price


def _cost(n_in: float, n_out: float, price: dict, n_cached: float) -> float:
    tier = _tier(price, n_in)
    cached_rate = tier.get("cached_input", tier["input"])
    return ((n_in - n_cached) * tier["input"] + n_cached * cached_rate + n_out * tier["output"]) / MTOK


def request_cost(n_in: int, n_out: int, price: dict, n_cached: int = 0) -> float:
    """Chi phí USD của một request.

    `n_in` là tổng token input, trong đó `n_cached` token đọc từ prompt cache (tính giá `cached_input`), phần còn lại
    tính giá `input`. `n_out` tính giá `output`. Nếu `price` có `long_context` và `n_in > threshold` thì mọi token
    của request tính theo bảng giá con đó. Số âm hoặc `n_cached > n_in` thì `ValueError`.
    """
    if min(n_in, n_out, n_cached) < 0:
        raise ValueError("số token không được âm")
    if n_cached > n_in:
        raise ValueError("n_cached không được lớn hơn n_in")
    return _cost(n_in, n_out, price, n_cached)


def monthly_cost(requests_per_day: float, n_in: int, n_out: int, price: dict,
                 cache_hit: float = 0.0, days: int = 30) -> float:
    """Chi phí USD của `days` ngày, mỗi ngày `requests_per_day` request giống nhau.

    `cache_hit` trong [0, 1] là tỉ lệ token input đọc từ cache (vd 0.8: 80% token input mỗi request là cache).
    Ngoài [0, 1] thì `ValueError`.
    """
    if not 0.0 <= cache_hit <= 1.0:
        raise ValueError("cache_hit phải trong [0, 1]")
    if min(n_in, n_out) < 0:
        raise ValueError("số token không được âm")
    # không làm tròn n_in * cache_hit: đây là kỳ vọng trên nhiều request
    return requests_per_day * days * _cost(n_in, n_out, price, n_in * cache_hit)


def self_hosted_cost_per_mtok(gpu_usd_per_hour: float, tokens_per_s: float, utilization: float = 1.0) -> float:
    """USD cho mỗi triệu token khi tự host: GPU giá `gpu_usd_per_hour`, sinh `tokens_per_s` token/giây lúc bận,
    bận `utilization` (0, 1] thời gian. Tham số không dương hoặc `utilization > 1` thì `ValueError`."""
    if gpu_usd_per_hour <= 0 or tokens_per_s <= 0 or not 0 < utilization <= 1:
        raise ValueError("tham số phải dương và utilization trong (0, 1]")
    tokens_per_hour = tokens_per_s * 3600 * utilization
    return gpu_usd_per_hour / tokens_per_hour * MTOK


def choose_model(candidates: list[dict], n_in: int, n_out: int, requests_per_day: float,
                 min_quality: float, max_latency_s: float) -> str | None:
    """Tên model rẻ nhất (theo `monthly_cost`, không cache) thoả cả chất lượng lẫn độ trễ, hoặc None.

    Mỗi ứng viên: {"name", "price", "quality", "ttft_s", "tokens_per_s"}. Độ trễ một request ước lượng là
    `ttft_s + n_out / tokens_per_s`. Đạt khi `quality >= min_quality` và độ trễ `<= max_latency_s`.
    Hai ứng viên bằng chi phí thì giữ ứng viên đứng trước trong danh sách.
    """
    best_name, best_cost = None, float("inf")
    for c in candidates:
        latency = c["ttft_s"] + n_out / c["tokens_per_s"]
        if c["quality"] < min_quality or latency > max_latency_s:
            continue
        cost = monthly_cost(requests_per_day, n_in, n_out, c["price"])
        if cost < best_cost:  # "<" chứ không "<=": bằng chi phí thì giữ ứng viên trước
            best_name, best_cost = c["name"], cost
    return best_name
