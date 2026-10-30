"""Máy tính chi phí LLM API: chi phí một request, mỗi 1 000 request, mỗi tháng, và vòng lặp agent.

Quy ước (xem README bài): giá tính bằng USD cho 1 triệu token (MTok). `Usage.input_tokens` là TỔNG token
input của request, đã gồm phần đọc từ cache (`cached_tokens`) và phần ghi vào cache (`cache_write_tokens`).
Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

from dataclasses import dataclass

MTOK = 1_000_000


@dataclass(frozen=True)
class Price:
    """Giá USD / 1 triệu token của một model."""

    input: float
    output: float
    cached_input: float | None = None  # giá token đọc từ cache; None: provider/model không có prompt caching
    cache_write: float | None = None  # giá token ghi vào cache; None: tính như input thường


@dataclass(frozen=True)
class Usage:
    """Số token của một request (hoặc tổng nhiều request)."""

    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    cache_write_tokens: int = 0


def request_cost(usage: Usage, price: Price) -> float:
    """Chi phí USD của một request."""
    # TODO
    raise NotImplementedError


def cost_per_1k_requests(usage: Usage, price: Price) -> float:
    """Chi phí USD cho 1 000 request giống nhau."""
    # TODO
    raise NotImplementedError


def monthly_cost(usage: Usage, price: Price, requests_per_day: float, days: int = 30) -> float:
    """Chi phí USD một tháng `days` ngày, mỗi ngày `requests_per_day` request."""
    # TODO
    raise NotImplementedError


def agent_loop_usage(
    prefix_tokens: int,
    step_output_tokens: int,
    tool_result_tokens: int,
    steps: int,
    cache_prefix: bool = False,
) -> Usage:
    """Tổng token của một vòng agent `steps` bước, mỗi bước là một lần gọi LLM.

    Bước i (từ 1) gửi lại toàn bộ hội thoại: prompt P_i = prefix + (i - 1) * (output + tool_result).
    Mỗi bước sinh `step_output_tokens`. Với `cache_prefix`, bước 1 ghi cả P_1 vào cache; bước i >= 2
    đọc P_{i-1} từ cache và ghi phần mới P_i - P_{i-1} vào cache.
    """
    # TODO
    raise NotImplementedError
