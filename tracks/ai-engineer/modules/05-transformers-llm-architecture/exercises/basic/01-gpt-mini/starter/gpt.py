"""GPT mini: Transformer decoder-only tự dựng bằng PyTorch (kiểu GPT-2, pre-norm, weight tying).

Tên module con được giữ cố định (module 08 gắn hook vào `blocks[i].attn`, `blocks[i].mlp`, `ln_f`, `lm_head`;
module 10 quantize các `nn.Linear`). Không dùng `nn.LayerNorm`, `nn.MultiheadAttention`,
`F.scaled_dot_product_attention`, `F.layer_norm` trong tệp này.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class GPTConfig:
    vocab_size: int = 8000
    block_size: int = 256
    n_layer: int = 4
    n_head: int = 4
    n_embd: int = 256
    dropout: float = 0.0


class LayerNorm(nn.Module):
    """Chuẩn hoá theo trục cuối: (x - mean) / sqrt(var + eps) * weight + bias, var là phương sai lệch (chia D)."""

    def __init__(self, dim: int, eps: float = 1e-5):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))
        self.bias = nn.Parameter(torch.zeros(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError


class CausalSelfAttention(nn.Module):
    """Multi-head self-attention có mask nhân quả.

    `qkv` chiếu (B, T, C) thành (B, T, 3C), tách theo thứ tự q | k | v; mỗi phần chia thành n_head head liên tiếp
    (head h là các cột h*head_dim .. (h+1)*head_dim). Score chia sqrt(head_dim). Vị trí t chỉ nhìn được 0..t.
    """

    def __init__(self, config: GPTConfig):
        super().__init__()
        if config.n_embd % config.n_head:
            raise ValueError("n_embd phải chia hết cho n_head")
        self.n_head = config.n_head
        self.head_dim = config.n_embd // config.n_head
        self.qkv = nn.Linear(config.n_embd, 3 * config.n_embd)
        self.proj = nn.Linear(config.n_embd, config.n_embd)
        self.attn_dropout = nn.Dropout(config.dropout)
        self.resid_dropout = nn.Dropout(config.dropout)
        # TODO: đăng ký mask nhân quả (block_size × block_size) làm buffer, không lưu vào state_dict
        raise NotImplementedError

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError


class MLP(nn.Module):
    def __init__(self, config: GPTConfig):
        super().__init__()
        self.fc = nn.Linear(config.n_embd, 4 * config.n_embd)
        self.act = nn.GELU()
        self.proj = nn.Linear(4 * config.n_embd, config.n_embd)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO: fc -> GELU -> proj -> dropout
        raise NotImplementedError


class Block(nn.Module):
    """Pre-norm: x + attn(ln1(x)), rồi + mlp(ln2(·))."""

    def __init__(self, config: GPTConfig):
        super().__init__()
        self.ln1 = LayerNorm(config.n_embd)
        self.attn = CausalSelfAttention(config)
        self.ln2 = LayerNorm(config.n_embd)
        self.mlp = MLP(config)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError


class GPT(nn.Module):
    """tok_emb + pos_emb -> dropout -> các Block -> ln_f -> lm_head (dùng chung trọng số với tok_emb).

    Khởi tạo: mọi Linear và Embedding N(0, 0.02), bias 0; riêng các trọng số `*.proj.weight` (lớp đổ về
    residual stream) N(0, 0.02 / sqrt(2 * n_layer)).
    """

    def __init__(self, config: GPTConfig):
        super().__init__()
        self.config = config
        self.tok_emb = nn.Embedding(config.vocab_size, config.n_embd)
        self.pos_emb = nn.Embedding(config.block_size, config.n_embd)
        self.drop = nn.Dropout(config.dropout)
        self.blocks = nn.ModuleList(Block(config) for _ in range(config.n_layer))
        self.ln_f = LayerNorm(config.n_embd)
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)
        # TODO: weight tying và khởi tạo theo docstring
        raise NotImplementedError

    def num_params(self, non_embedding: bool = False) -> int:
        """Số tham số (trọng số dùng chung chỉ đếm một lần); non_embedding=True thì trừ tok_emb và pos_emb."""
        # TODO
        raise NotImplementedError

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None):
        """idx (B, T) với T <= block_size (vượt thì ValueError). Trả (logits (B, T, V), loss hoặc None).

        loss là cross-entropy trung bình trên mọi vị trí, bỏ qua vị trí có target -1.
        """
        # TODO
        raise NotImplementedError

    @torch.no_grad()
    def generate(
        self,
        idx: torch.Tensor,
        max_new_tokens: int,
        temperature: float = 1.0,
        top_k: int | None = None,
        generator: torch.Generator | None = None,
    ) -> torch.Tensor:
        """Sinh thêm max_new_tokens token, trả (B, T + max_new_tokens).

        Mỗi bước chỉ đưa vào block_size token cuối. temperature == 0: argmax; ngược lại chia temperature, giữ top_k
        logits lớn nhất nếu top_k khác None, rồi torch.multinomial với `generator`. Chạy ở chế độ eval và trả lại
        chế độ train/eval như trước khi gọi.
        """
        # TODO
        raise NotImplementedError
