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
    # TODO: scores = q @ kᵀ / sqrt(d_k)
    # TODO: che vị trí mask == False bằng -inf (masked_fill), softmax theo trục key
    raise NotImplementedError


def causal_mask(length: int) -> torch.Tensor:
    """Mask (length, length) kiểu bool: query i được nhìn key j khi j <= i."""
    # TODO
    raise NotImplementedError


def padding_mask(lengths: torch.Tensor, max_len: int) -> torch.Tensor:
    """Mask (B, max_len) kiểu bool: True ở các vị trí thật (j < lengths[b]), False ở padding."""
    # TODO
    raise NotImplementedError
