"""Scaled dot-product attention tự viết, đối chiếu với torch.nn.functional.

Không gọi F.scaled_dot_product_attention hay nn.MultiheadAttention trong tệp này.
Quy ước mask giống PyTorch: tensor bool, True = được phép nhìn, False = bị che.
"""

from __future__ import annotations

import math

import torch


def scaled_dot_product_attention(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor,
                                 mask: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """softmax(q kᵀ / sqrt(d_k)) v.

    q: (..., Lq, d_k), k: (..., Lk, d_k), v: (..., Lk, d_v); các chiều "..." giống nhau.
    mask: bool, broadcast được về (..., Lq, Lk); vị trí False nhận trọng số đúng bằng 0.
    Trả về (output (..., Lq, d_v), weights (..., Lq, Lk)).
    Giả định mỗi query còn ít nhất một key được nhìn.
    """
    d_k = q.size(-1)
    scores = q @ k.transpose(-2, -1) / math.sqrt(d_k)
    if mask is not None:
        scores = scores.masked_fill(~mask, float("-inf"))
    weights = torch.softmax(scores, dim=-1)     # softmax của PyTorch đã trừ max: ổn định số
    return weights @ v, weights


def causal_mask(length: int) -> torch.Tensor:
    """Mask (length, length) kiểu bool: query i được nhìn key j khi j <= i."""
    return torch.ones(length, length, dtype=torch.bool).tril()


def padding_mask(lengths: torch.Tensor, max_len: int) -> torch.Tensor:
    """Mask (B, max_len) kiểu bool: True ở các vị trí thật (j < lengths[b]), False ở padding."""
    return torch.arange(max_len)[None, :] < lengths[:, None]
