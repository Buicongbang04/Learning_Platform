"""GPT mini: Transformer decoder-only tự dựng bằng PyTorch (kiểu GPT-2, pre-norm, weight tying).

Tên module con được giữ cố định (module 08 gắn hook vào `blocks[i].attn`, `blocks[i].mlp`, `ln_f`, `lm_head`;
module 10 quantize các `nn.Linear`). Không dùng `nn.LayerNorm`, `nn.MultiheadAttention`,
`F.scaled_dot_product_attention`, `F.layer_norm` trong tệp này.

Ghi chú cho module dùng lại lớp này:
- Ma trận attention (B, n_head, T, T) sau softmax đọc được bằng forward hook trên `blocks[i].attn.attn_dropout`
  (output của hook là ma trận đó; dropout = 0 khi eval).
- `lm_head.weight` là cùng một tensor với `tok_emb.weight`: quantize hoặc sửa `lm_head` sẽ đổi luôn embedding.
- `generate` không có KV cache (mỗi bước forward lại tối đa `block_size` token); bản có cache là `ModernGPT` của module 05,
  bài Advanced 02.
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
        mean = x.mean(dim=-1, keepdim=True)
        var = (x - mean).pow(2).mean(dim=-1, keepdim=True)
        return (x - mean) / torch.sqrt(var + self.eps) * self.weight + self.bias


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
        mask = torch.tril(torch.ones(config.block_size, config.block_size, dtype=torch.bool))
        self.register_buffer("mask", mask.view(1, 1, config.block_size, config.block_size), persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        q, k, v = self.qkv(x).split(C, dim=2)
        q, k, v = (t.view(B, T, self.n_head, self.head_dim).transpose(1, 2) for t in (q, k, v))
        scores = q @ k.transpose(-2, -1) / math.sqrt(self.head_dim)
        scores = scores.masked_fill(~self.mask[:, :, :T, :T], float("-inf"))
        att = self.attn_dropout(torch.softmax(scores, dim=-1))
        y = (att @ v).transpose(1, 2).contiguous().view(B, T, C)
        return self.resid_dropout(self.proj(y))


class MLP(nn.Module):
    def __init__(self, config: GPTConfig):
        super().__init__()
        self.fc = nn.Linear(config.n_embd, 4 * config.n_embd)
        self.act = nn.GELU()
        self.proj = nn.Linear(4 * config.n_embd, config.n_embd)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.proj(self.act(self.fc(x))))


class Block(nn.Module):
    """Pre-norm: x + attn(ln1(x)), rồi + mlp(ln2(·))."""

    def __init__(self, config: GPTConfig):
        super().__init__()
        self.ln1 = LayerNorm(config.n_embd)
        self.attn = CausalSelfAttention(config)
        self.ln2 = LayerNorm(config.n_embd)
        self.mlp = MLP(config)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        return x + self.mlp(self.ln2(x))


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
        self.lm_head.weight = self.tok_emb.weight
        self.apply(self._init_weights)
        for name, p in self.named_parameters():
            if name.endswith("proj.weight"):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * config.n_layer))

    @staticmethod
    def _init_weights(module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def num_params(self, non_embedding: bool = False) -> int:
        """Số tham số (trọng số dùng chung chỉ đếm một lần); non_embedding=True thì trừ tok_emb và pos_emb."""
        n = sum(p.numel() for p in self.parameters())
        if non_embedding:
            n -= self.tok_emb.weight.numel() + self.pos_emb.weight.numel()
        return n

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None):
        """idx (B, T) với T <= block_size (vượt thì ValueError). Trả (logits (B, T, V), loss hoặc None).

        loss là cross-entropy trung bình trên mọi vị trí, bỏ qua vị trí có target -1.
        """
        B, T = idx.shape
        if T > self.config.block_size:
            raise ValueError(f"chuỗi dài {T} vượt block_size {self.config.block_size}")
        pos = torch.arange(T, device=idx.device)
        x = self.drop(self.tok_emb(idx) + self.pos_emb(pos))
        for block in self.blocks:
            x = block(x)
        logits = self.lm_head(self.ln_f(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.reshape(-1), ignore_index=-1)
        return logits, loss

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

        Mỗi bước chỉ đưa vào block_size token cuối, không có KV cache. temperature == 0: argmax; ngược lại chia
        temperature, giữ top_k logits lớn nhất nếu top_k khác None, rồi torch.multinomial với `generator`. Chạy ở chế độ
        eval và trả lại chế độ train/eval như trước khi gọi.
        """
        was_training = self.training
        self.eval()
        for _ in range(max_new_tokens):
            logits, _ = self(idx[:, -self.config.block_size:])
            logits = logits[:, -1, :]
            if temperature == 0:
                nxt = logits.argmax(dim=-1, keepdim=True)
            else:
                logits = logits / temperature
                if top_k is not None:
                    kth = torch.topk(logits, min(top_k, logits.size(-1)), dim=-1).values[:, -1:]
                    logits = logits.masked_fill(logits < kth, float("-inf"))
                nxt = torch.multinomial(torch.softmax(logits, dim=-1), 1, generator=generator)
            idx = torch.cat([idx, nxt], dim=1)
        self.train(was_training)
        return idx
