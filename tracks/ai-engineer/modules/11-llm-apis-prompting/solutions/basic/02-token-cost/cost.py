"""Chi phí gọi LLM API theo token: một request, một workload hằng tháng, điểm hoà vốn của prompt caching.

Giá luôn là THAM SỐ (USD cho mỗi triệu token, "per MTok"), không bao giờ viết cứng trong code: giá đổi vài tháng
một lần. Chỉ dùng thư viện chuẩn.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MTOK = 1_000_000


@dataclass(frozen=True)
class Price:
    input: float
    output: float
    cache_write: float | None = None
    cache_read: float | None = None
    batch_discount: float = 0.5


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0


def request_cost(usage: Usage, price: Price, *, batch: bool = False) -> float:
    counts = (usage.input_tokens, usage.output_tokens, usage.cache_write_tokens, usage.cache_read_tokens)
    if any(c < 0 for c in counts):
        raise ValueError("số token không được âm")
    if usage.cache_write_tokens and price.cache_write is None:
        raise ValueError("có cache_write_tokens nhưng bảng giá không có giá ghi cache")
    if usage.cache_read_tokens and price.cache_read is None:
        raise ValueError("có cache_read_tokens nhưng bảng giá không có giá đọc cache")
    total = (usage.input_tokens * price.input + usage.output_tokens * price.output
             + usage.cache_write_tokens * (price.cache_write or 0.0)
             + usage.cache_read_tokens * (price.cache_read or 0.0)) / MTOK
    return total * (1 - price.batch_discount) if batch else total


def workload_cost(n_requests: int, prompt_tokens: int, output_tokens: int, price: Price, *,
                  cached_prefix_tokens: int = 0, cache_hit_rate: float = 0.0, batch: bool = False) -> float:
    if not 0.0 <= cache_hit_rate <= 1.0:
        raise ValueError("cache_hit_rate phải trong [0, 1]")
    if not 0 <= cached_prefix_tokens <= prompt_tokens:
        raise ValueError("cached_prefix_tokens phải trong [0, prompt_tokens]")
    rest = prompt_tokens - cached_prefix_tokens
    per_request = 0.0
    if cache_hit_rate > 0:
        hit = Usage(rest, output_tokens, cache_read_tokens=cached_prefix_tokens)
        per_request += cache_hit_rate * request_cost(hit, price, batch=batch)
    if cache_hit_rate < 1:
        miss = Usage(rest, output_tokens, cache_write_tokens=cached_prefix_tokens)
        per_request += (1 - cache_hit_rate) * request_cost(miss, price, batch=batch)
    return n_requests * per_request


def cache_breakeven(price: Price) -> int:
    if price.cache_write is None or price.cache_read is None:
        raise ValueError("bảng giá không có giá cache")
    extra = price.cache_write - price.input
    saving = price.input - price.cache_read
    if saving <= 0:
        raise ValueError("đọc cache không rẻ hơn input thường: caching không bao giờ hoà vốn")
    if extra <= 0:
        return 0
    return math.ceil(extra / saving - 1e-12)


def rank_models(prices: dict[str, Price], n_requests: int, prompt_tokens: int, output_tokens: int,
                **kwargs) -> list[tuple[str, float]]:
    costs = [(name, workload_cost(n_requests, prompt_tokens, output_tokens, p, **kwargs)) for name, p in prices.items()]
    return sorted(costs, key=lambda item: (item[1], item[0]))
