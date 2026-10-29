"""Transformer encoder nhỏ để phân loại văn bản, viết từ các khối cơ bản.

Được dùng nn.Linear, nn.LayerNorm, nn.Embedding, nn.Dropout, torch.softmax, và
F.scaled_dot_product_attention (bài Basic 03 đã tự viết phần đó). Không dùng nn.MultiheadAttention
hay nn.TransformerEncoderLayer trong tệp này (test dùng chúng để đối chiếu).
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F
from torch import nn


def sinusoidal_positional_encoding(max_len: int, d_model: int) -> torch.Tensor:
    """(max_len, d_model): cột chẵn sin(pos / 10000^(2i/d)), cột lẻ cos cùng góc. d_model chẵn."""
    # TODO
    raise NotImplementedError


class MultiHeadSelfAttention(nn.Module):
    """Self-attention nhiều head.

    Bắt buộc có: self.qkv = nn.Linear(d_model, 3 * d_model) (hàng xếp chồng q, k, v giống
    in_proj_weight của PyTorch) và self.out = nn.Linear(d_model, d_model).
    key_padding_mask: bool (B, L), True = vị trí padding (quy ước của nn.MultiheadAttention).
    ValueError nếu d_model không chia hết cho n_heads.
    """

    def __init__(self, d_model: int, n_heads: int, dropout: float = 0.0):
        super().__init__()
        # TODO
        raise NotImplementedError

    def forward(self, x: torch.Tensor, key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        # TODO: (B, L, d) → q, k, v (B, h, L, d/h) → attention → ghép head → self.out
        raise NotImplementedError


class EncoderBlock(nn.Module):
    """Khối encoder pre-LN: x = x + Dropout(Attn(LN1(x))); x = x + Dropout(FFN(LN2(x))).

    FFN = Linear(d_model, d_ff) → GELU → Linear(d_ff, d_model).
    """

    def __init__(self, d_model: int, n_heads: int, d_ff: int, dropout: float = 0.0):
        super().__init__()
        # TODO
        raise NotImplementedError

    def forward(self, x: torch.Tensor, key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        # TODO
        raise NotImplementedError


class TransformerClassifier(nn.Module):
    """Embedding (padding_idx=0) * sqrt(d_model) + positional encoding (buffer) → n_layers EncoderBlock
    → LayerNorm → trung bình các vị trí không phải padding → Linear(d_model, 1). Trả logits (N,).

    Token id 0 là padding.
    """

    def __init__(self, vocab_size: int, d_model: int = 32, n_heads: int = 4, n_layers: int = 2,
                 d_ff: int = 64, max_len: int = 64, dropout: float = 0.1):
        super().__init__()
        # TODO
        raise NotImplementedError

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError
