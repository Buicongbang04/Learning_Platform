"""Ước lượng bộ nhớ GPU khi serve LLM: trọng số, KV cache, số request chạy song song, context tối đa.

Đơn vị: byte (số thực cho trọng số vì bits/weight có thể lẻ, như 4.85 của Q4_K_M; số nguyên cho KV cache).
Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

GiB = 1024**3


@dataclass(frozen=True)
class ModelShape:
    """Các số của một decoder-only transformer cần cho ước lượng bộ nhớ."""

    n_params: float
    n_layers: int
    n_kv_heads: int
    head_dim: int


def shape_from_hf_config(config: dict, n_params: float) -> ModelShape:
    """Đọc `config.json` kiểu Hugging Face (Llama/Qwen/Mistral/Gemma...) thành ModelShape."""
    # TODO
    raise NotImplementedError


def weight_bytes(n_params: float, bits_per_weight: float) -> float:
    """Bộ nhớ trọng số: n_params * bits / 8."""
    # TODO
    raise NotImplementedError


def kv_bytes_per_token(shape: ModelShape, kv_bits: int = 16) -> int:
    """Byte KV cache cho MỘT token: K và V, ở mọi layer, mọi KV head."""
    # TODO
    raise NotImplementedError


def kv_cache_bytes(shape: ModelShape, context_tokens: int, batch: int = 1, kv_bits: int = 16) -> int:
    """KV cache cho `batch` chuỗi, mỗi chuỗi `context_tokens` token."""
    # TODO
    raise NotImplementedError


def max_concurrent_sequences(
    vram_bytes: float,
    shape: ModelShape,
    weight_bits: float,
    context_tokens: int,
    kv_bits: int = 16,
    reserve_bytes: float = 0,
) -> int:
    """Số chuỗi tối đa chạy cùng lúc, mỗi chuỗi giữ đủ KV cache cho `context_tokens` token.

    Bộ nhớ cho KV = vram - reserve (activation, CUDA context, phân mảnh) - trọng số. 0 nếu không vừa.
    """
    # TODO
    raise NotImplementedError


def max_context_tokens(
    vram_bytes: float,
    shape: ModelShape,
    weight_bits: float,
    batch: int = 1,
    kv_bits: int = 16,
    reserve_bytes: float = 0,
) -> int:
    """Context dài nhất (token) mỗi chuỗi khi chạy `batch` chuỗi cùng lúc. 0 nếu không vừa."""
    # TODO
    raise NotImplementedError
