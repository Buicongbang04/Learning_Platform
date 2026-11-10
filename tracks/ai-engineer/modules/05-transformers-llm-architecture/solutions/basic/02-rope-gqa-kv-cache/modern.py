"""Các mảnh của một LLM hiện đại kiểu Llama: RMSNorm, RoPE, SwiGLU, grouped-query attention, KV cache."""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps) * self.weight


def rope_cache(head_dim: int, max_len: int, base: float = 10000.0) -> tuple[torch.Tensor, torch.Tensor]:
    if head_dim % 2:
        raise ValueError("head_dim phải chẵn")
    inv_freq = base ** (-torch.arange(0, head_dim, 2, dtype=torch.float64) / head_dim)
    angles = torch.outer(torch.arange(max_len, dtype=torch.float64), inv_freq)
    angles = torch.cat([angles, angles], dim=-1)
    return angles.cos().float(), angles.sin().float()


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat([-x2, x1], dim=-1)


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor, start_pos: int = 0) -> torch.Tensor:
    T = x.shape[-2]
    c = cos[start_pos:start_pos + T].to(x.dtype)
    s = sin[start_pos:start_pos + T].to(x.dtype)
    return x * c + rotate_half(x) * s


def repeat_kv(x: torch.Tensor, n_rep: int) -> torch.Tensor:
    if n_rep == 1:
        return x
    B, H, T, D = x.shape
    return x[:, :, None, :, :].expand(B, H, n_rep, T, D).reshape(B, H * n_rep, T, D)


class SwiGLU(nn.Module):
    def __init__(self, dim: int, hidden: int):
        super().__init__()
        self.w1 = nn.Linear(dim, hidden, bias=False)
        self.w3 = nn.Linear(dim, hidden, bias=False)
        self.w2 = nn.Linear(hidden, dim, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class GQAttention(nn.Module):
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
        cos, sin = rope_cache(self.head_dim, max_len, rope_base)
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)

    def forward(self, x: torch.Tensor, kv_cache: tuple[torch.Tensor, torch.Tensor] | None = None):
        B, T, _ = x.shape
        q = self.wq(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = self.wk(x).view(B, T, self.n_kv_head, self.head_dim).transpose(1, 2)
        v = self.wv(x).view(B, T, self.n_kv_head, self.head_dim).transpose(1, 2)
        past = 0 if kv_cache is None else kv_cache[0].shape[2]
        q = apply_rope(q, self.cos, self.sin, past)
        k = apply_rope(k, self.cos, self.sin, past)
        if kv_cache is not None:
            k = torch.cat([kv_cache[0], k], dim=2)
            v = torch.cat([kv_cache[1], v], dim=2)
        new_cache = (k, v)
        n_rep = self.n_head // self.n_kv_head
        k, v = repeat_kv(k, n_rep), repeat_kv(v, n_rep)
        scores = q @ k.transpose(-2, -1) / math.sqrt(self.head_dim)
        S = k.shape[2]
        allowed = torch.ones(T, S, dtype=torch.bool, device=x.device).tril(diagonal=past)
        scores = scores.masked_fill(~allowed, float("-inf"))
        y = torch.softmax(scores.float(), dim=-1).to(q.dtype) @ v
        return self.wo(y.transpose(1, 2).reshape(B, T, -1)), new_cache


def kv_cache_bytes(n_layer: int, n_kv_head: int, head_dim: int, seq_len: int, batch: int = 1,
                   bytes_per_elem: int = 2) -> int:
    return 2 * n_layer * n_kv_head * head_dim * seq_len * batch * bytes_per_elem
