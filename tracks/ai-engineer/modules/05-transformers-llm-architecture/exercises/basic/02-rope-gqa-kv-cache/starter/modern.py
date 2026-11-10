"""Các mảnh của một LLM hiện đại kiểu Llama: RMSNorm, RoPE, SwiGLU, grouped-query attention, KV cache.

Quy ước shape trong attention: (B, H, T, D) với H là số head, D = head_dim. Không dùng
`F.scaled_dot_product_attention`, `nn.MultiheadAttention`, `nn.RMSNorm` trong tệp này.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class RMSNorm(nn.Module):
    """x / sqrt(mean(x^2) + eps) * weight. Không trừ trung bình, không có bias."""

    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError


def rope_cache(head_dim: int, max_len: int, base: float = 10000.0) -> tuple[torch.Tensor, torch.Tensor]:
    """Trả (cos, sin), mỗi tensor float32 shape (max_len, head_dim).

    Tần số theta_i = base^(-2i / head_dim) với i = 0 .. head_dim/2 - 1; góc ở vị trí m là m * theta_i.
    Cột i và cột i + head_dim/2 mang cùng góc (quy ước "rotate half" của Llama/GPT-NeoX). head_dim lẻ: ValueError.
    """
    # TODO
    raise NotImplementedError


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    """Nửa đầu x1, nửa sau x2 theo trục cuối; trả [-x2, x1]."""
    # TODO
    raise NotImplementedError


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor, start_pos: int = 0) -> torch.Tensor:
    """x (..., T, head_dim): token thứ t có vị trí tuyệt đối start_pos + t. Quay cặp (i, i + head_dim/2)."""
    # TODO
    raise NotImplementedError


def repeat_kv(x: torch.Tensor, n_rep: int) -> torch.Tensor:
    """(B, H_kv, T, D) -> (B, H_kv * n_rep, T, D); head truy vấn h dùng kv head h // n_rep."""
    # TODO
    raise NotImplementedError


class SwiGLU(nn.Module):
    """w2(silu(w1 x) * w3 x), ba lớp không bias."""

    def __init__(self, dim: int, hidden: int):
        super().__init__()
        self.w1 = nn.Linear(dim, hidden, bias=False)
        self.w3 = nn.Linear(dim, hidden, bias=False)
        self.w2 = nn.Linear(hidden, dim, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError


class GQAttention(nn.Module):
    """Grouped-query attention nhân quả có RoPE và KV cache.

    wq: dim -> n_head * head_dim; wk, wv: dim -> n_kv_head * head_dim; wo: n_head * head_dim -> dim (không bias).
    RoPE áp lên q và k (không áp lên v) theo vị trí tuyệt đối. Buffer `cos`, `sin` từ rope_cache(head_dim, max_len).
    """

    def __init__(self, dim: int, n_head: int, n_kv_head: int, max_len: int, rope_base: float = 10000.0):
        super().__init__()
        if dim % n_head or n_head % n_kv_head:
            raise ValueError("dim chia hết cho n_head, n_head chia hết cho n_kv_head")
        self.n_head = n_head
        self.n_kv_head = n_kv_head
        self.head_dim = dim // n_head
        self.wq = nn.Linear(dim, n_head * self.head_dim, bias=False)
        self.wk = nn.Linear(dim, n_kv_head * self.head_dim, bias=False)
        self.wv = nn.Linear(dim, n_kv_head * self.head_dim, bias=False)
        self.wo = nn.Linear(n_head * self.head_dim, dim, bias=False)
        # TODO: đăng ký buffer cos, sin (persistent=False)
        raise NotImplementedError

    def forward(self, x: torch.Tensor, kv_cache: tuple[torch.Tensor, torch.Tensor] | None = None):
        """x (B, T, dim). kv_cache là (k, v) của các token trước, shape (B, n_kv_head, T_past, head_dim), k đã quay RoPE.

        Trả (out (B, T, dim), new_cache) với new_cache gồm cả token cũ và T token mới, lưu TRƯỚC khi repeat_kv.
        Token mới thứ t (vị trí T_past + t) nhìn được mọi token cũ và token mới 0..t.
        """
        # TODO
        raise NotImplementedError


def kv_cache_bytes(n_layer: int, n_kv_head: int, head_dim: int, seq_len: int, batch: int = 1,
                   bytes_per_elem: int = 2) -> int:
    """Số byte của KV cache (cả K và V, mọi layer) cho batch chuỗi dài seq_len."""
    # TODO
    raise NotImplementedError
