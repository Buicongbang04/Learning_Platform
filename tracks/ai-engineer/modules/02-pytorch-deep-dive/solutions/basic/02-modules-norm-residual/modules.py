"""nn.Module từ bên trong: RMSNorm, GroupNorm tự viết, block residual pre-norm, weight tying (lời giải mẫu)."""

from __future__ import annotations

import torch
from torch import nn


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        xf = x.to(torch.promote_types(x.dtype, torch.float32))       # bf16/fp16 -> fp32, fp64 giữ nguyên
        out = xf * torch.rsqrt(xf.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return (out * self.weight.to(xf.dtype)).to(x.dtype)


def group_norm(
    x: torch.Tensor,
    num_groups: int,
    weight: torch.Tensor | None = None,
    bias: torch.Tensor | None = None,
    eps: float = 1e-5,
) -> torch.Tensor:
    n, c = x.shape[:2]
    if c % num_groups:
        raise ValueError(f"{c} kênh không chia hết cho {num_groups} nhóm")
    g = x.reshape(n, num_groups, -1)
    mean = g.mean(dim=-1, keepdim=True)
    var = g.var(dim=-1, unbiased=False, keepdim=True)
    out = ((g - mean) / torch.sqrt(var + eps)).reshape(x.shape)
    shape = (1, c) + (1,) * (x.dim() - 2)
    if weight is not None:
        out = out * weight.reshape(shape)
    if bias is not None:
        out = out + bias.reshape(shape)
    return out


class Block(nn.Module):
    def __init__(self, dim: int, zero_init: bool = True):
        super().__init__()
        self.norm = RMSNorm(dim)
        self.fc1 = nn.Linear(dim, 4 * dim)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(4 * dim, dim)
        if zero_init:
            nn.init.zeros_(self.fc2.weight)
            nn.init.zeros_(self.fc2.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.fc2(self.act(self.fc1(self.norm(x))))


class TinyLM(nn.Module):
    def __init__(self, vocab_size: int, dim: int, n_layers: int, zero_init: bool = True):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, dim)
        self.blocks = nn.ModuleList([Block(dim, zero_init) for _ in range(n_layers)])
        self.norm = RMSNorm(dim)
        self.head = nn.Linear(dim, vocab_size, bias=False)
        self.head.weight = self.embed.weight

    def forward(self, idx: torch.Tensor) -> torch.Tensor:
        x = self.embed(idx)
        for block in self.blocks:
            x = block(x)
        return self.head(self.norm(x))


def weight_decay_groups(model: nn.Module, weight_decay: float) -> list[dict]:
    decay, no_decay = [], []
    for p in model.parameters():
        if not p.requires_grad:
            continue
        (decay if p.dim() >= 2 else no_decay).append(p)
    return [
        {"params": decay, "weight_decay": weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]


def parameter_report(model: nn.Module) -> dict[str, int]:
    params = list(model.parameters())
    buffers = list(model.buffers())
    return {
        "total": sum(p.numel() for p in params),
        "trainable": sum(p.numel() for p in params if p.requires_grad),
        "buffers": sum(b.numel() for b in buffers),
        "bytes": sum(t.numel() * t.element_size() for t in params + buffers),
    }
