"""Hai hướng mở rộng Transformer: Mixture-of-Experts (MoE) và state space model chọn lọc (Mamba)."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class Expert(nn.Module):
    def __init__(self, dim: int, hidden: int):
        super().__init__()
        self.fc = nn.Linear(dim, hidden)
        self.proj = nn.Linear(hidden, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.proj(F.gelu(self.fc(x)))


class MoE(nn.Module):
    def __init__(self, dim: int, hidden: int, n_experts: int, top_k: int):
        super().__init__()
        if not 1 <= top_k <= n_experts:
            raise ValueError("1 <= top_k <= n_experts")
        self.n_experts = n_experts
        self.top_k = top_k
        self.gate = nn.Linear(dim, n_experts, bias=False)
        self.experts = nn.ModuleList(Expert(dim, hidden) for _ in range(n_experts))

    def route(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        logits = self.gate(x)
        top_logits, top_idx = logits.topk(self.top_k, dim=-1)
        weights = torch.softmax(top_logits, dim=-1)
        return top_idx, weights, torch.softmax(logits, dim=-1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        shape = x.shape
        x = x.reshape(-1, shape[-1])
        top_idx, weights, probs = self.route(x)
        out = torch.zeros_like(x)
        for e, expert in enumerate(self.experts):
            token, slot = (top_idx == e).nonzero(as_tuple=True)
            if token.numel():
                out.index_add_(0, token, expert(x[token]) * weights[token, slot, None])
        return out.reshape(shape), load_balancing_loss(probs, top_idx, self.n_experts)


def load_balancing_loss(probs: torch.Tensor, top_idx: torch.Tensor, n_experts: int) -> torch.Tensor:
    counts = F.one_hot(top_idx, n_experts).sum(dim=(0, 1)).to(probs.dtype)
    f = counts / top_idx.numel()
    p = probs.mean(dim=0)
    return n_experts * (f * p).sum()


def discretize(A: torch.Tensor, B: torch.Tensor, delta: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    A_bar = torch.exp(delta * A)
    return A_bar, (A_bar - 1) / A * B


def ssm_scan(A_bar: torch.Tensor, B_bar: torch.Tensor, C: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    T, D = x.shape
    h = x.new_zeros(D, A_bar.shape[-1])
    ys = []
    for t in range(T):
        h = A_bar[t] * h + B_bar[t] * x[t, :, None]
        ys.append((h * C[t]).sum(-1))
    return torch.stack(ys)


def ssm_kernel(A_bar: torch.Tensor, B_bar: torch.Tensor, C: torch.Tensor, length: int) -> torch.Tensor:
    k = torch.arange(length, dtype=A_bar.dtype)[:, None, None]
    return (A_bar[None] ** k * B_bar[None] * C[None]).sum(-1)


def causal_conv(x: torch.Tensor, kernel: torch.Tensor) -> torch.Tensor:
    T = x.shape[0]
    y = torch.zeros_like(x)
    for k in range(T):
        y[k:] += kernel[k] * x[:T - k]
    return y


def selective_scan(x: torch.Tensor, delta: torch.Tensor, A: torch.Tensor, B: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
    A_bar, B_bar = discretize(A[None], B[:, None, :], delta[:, :, None])
    return ssm_scan(A_bar, B_bar, C[:, None, :], x)
