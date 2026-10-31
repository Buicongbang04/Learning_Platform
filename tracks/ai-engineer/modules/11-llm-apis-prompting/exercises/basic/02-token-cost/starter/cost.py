"""Chi phí gọi LLM API theo token: một request, một workload hằng tháng, điểm hoà vốn của prompt caching.

Giá luôn là THAM SỐ (USD cho mỗi triệu token, "per MTok"), không bao giờ viết cứng trong code: giá đổi vài tháng
một lần. Chỉ dùng thư viện chuẩn. Đọc README của bài cho định nghĩa đầy đủ.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MTOK = 1_000_000


@dataclass(frozen=True)
class Price:
    input: float                       # USD / MTok token vào không cache
    output: float                      # USD / MTok token ra
    cache_write: float | None = None   # USD / MTok token ghi vào cache (None: không hỗ trợ)
    cache_read: float | None = None    # USD / MTok token đọc từ cache
    batch_discount: float = 0.5        # Batch API giảm 50% mọi loại token


@dataclass(frozen=True)
class Usage:
    input_tokens: int                  # token vào KHÔNG thuộc cache
    output_tokens: int
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0


def request_cost(usage: Usage, price: Price, *, batch: bool = False) -> float:
    """Chi phí USD của một request. ValueError: số token âm, hoặc có token cache mà bảng giá thiếu giá đó."""
    # TODO
    raise NotImplementedError


def workload_cost(n_requests: int, prompt_tokens: int, output_tokens: int, price: Price, *,
                  cached_prefix_tokens: int = 0, cache_hit_rate: float = 0.0, batch: bool = False) -> float:
    """Chi phí kỳ vọng của n_requests request giống nhau.

    `prompt_tokens` là tổng token vào của một request, trong đó `cached_prefix_tokens` đầu tiên là prefix chung.
    Tỉ lệ `cache_hit_rate` request đọc prefix từ cache, phần còn lại ghi prefix vào cache. ValueError khi tỉ lệ ngoài
    [0, 1] hoặc prefix ngoài [0, prompt_tokens].
    """
    # TODO
    raise NotImplementedError


def cache_breakeven(price: Price) -> int:
    """Số lần ĐỌC cache tối thiểu sau một lần ghi để tổng chi phí phần prefix không cao hơn khi không cache.

    0 khi ghi cache không đắt hơn input thường. ValueError khi thiếu giá cache, hoặc đọc cache không rẻ hơn input.
    """
    # TODO
    raise NotImplementedError


def rank_models(prices: dict[str, Price], n_requests: int, prompt_tokens: int, output_tokens: int,
                **kwargs) -> list[tuple[str, float]]:
    """[(tên model, chi phí workload)] từ rẻ tới đắt, hoà thì theo tên; kwargs chuyển cho workload_cost."""
    # TODO
    raise NotImplementedError
