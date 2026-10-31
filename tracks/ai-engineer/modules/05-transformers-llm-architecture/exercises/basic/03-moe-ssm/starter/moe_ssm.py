"""Hai hướng mở rộng Transformer: Mixture-of-Experts (MoE) và state space model chọn lọc (Mamba).

Phần SSM dùng A chéo (mỗi kênh d, mỗi chiều trạng thái n một số âm), x shape (T, D), trạng thái h shape (D, N).
Chỉ dùng torch; vòng lặp theo thời gian là được (bài này cần đúng, chưa cần nhanh).
"""

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
    """Lớp MoE thay cho MLP: router `gate` chọn top_k expert cho mỗi token."""

    def __init__(self, dim: int, hidden: int, n_experts: int, top_k: int):
        super().__init__()
        if not 1 <= top_k <= n_experts:
            raise ValueError("1 <= top_k <= n_experts")
        self.n_experts = n_experts
        self.top_k = top_k
        self.gate = nn.Linear(dim, n_experts, bias=False)
        self.experts = nn.ModuleList(Expert(dim, hidden) for _ in range(n_experts))

    def route(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """x (N, dim). Trả (top_idx (N, k) theo thứ tự logit giảm dần, weights (N, k) = softmax trên k logit được chọn,
        probs (N, n_experts) = softmax trên mọi logit)."""
        # TODO
        raise NotImplementedError

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """x (..., dim). Trả (out cùng shape, aux = load_balancing_loss).

        out của token = tổng có trọng số output của k expert được chọn. Mỗi expert chỉ được gọi trên các token route
        tới nó (gọi một lần với mọi token đó), không chạy trên token khác.
        """
        # TODO
        raise NotImplementedError


def load_balancing_loss(probs: torch.Tensor, top_idx: torch.Tensor, n_experts: int) -> torch.Tensor:
    """Loss cân tải kiểu Switch Transformer: n_experts * sum_i f_i * P_i.

    f_i = số lần expert i được chọn / tổng số lượt chọn (N * k); P_i = trung bình probs[:, i] trên N token.
    Bằng 1 khi route đều, bằng n_experts khi mọi token dồn về một expert với xác suất 1.
    """
    # TODO
    raise NotImplementedError


def discretize(A: torch.Tensor, B: torch.Tensor, delta: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Zero-order hold cho A chéo (phép toán từng phần tử, broadcast): A_bar = exp(ΔA), B_bar = (exp(ΔA) - 1) / A · B."""
    # TODO
    raise NotImplementedError


def ssm_scan(A_bar: torch.Tensor, B_bar: torch.Tensor, C: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """Hồi quy h_t = A_bar[t] * h_{t-1} + B_bar[t] * x_t, y_t[d] = sum_n C[t][d, n] * h_t[d, n], h_{-1} = 0.

    A_bar, B_bar, C index được theo t, mỗi phần tử broadcast được về (D, N). x (T, D). Trả y (T, D).
    """
    # TODO
    raise NotImplementedError


def ssm_kernel(A_bar: torch.Tensor, B_bar: torch.Tensor, C: torch.Tensor, length: int) -> torch.Tensor:
    """SSM bất biến theo thời gian (A_bar, B_bar, C shape (D, N)): kernel K[k, d] = sum_n C A_bar^k B_bar. Trả (length, D)."""
    # TODO
    raise NotImplementedError


def causal_conv(x: torch.Tensor, kernel: torch.Tensor) -> torch.Tensor:
    """Tích chập nhân quả theo từng kênh: y[t, d] = sum_{k=0..t} kernel[k, d] * x[t - k, d]. x, kernel shape (T, D)."""
    # TODO
    raise NotImplementedError


def selective_scan(x: torch.Tensor, delta: torch.Tensor, A: torch.Tensor, B: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
    """SSM chọn lọc (S6 của Mamba, bản không có skip D và cổng): Δ, B, C phụ thuộc token.

    x (T, D), delta (T, D) dương, A (D, N) âm, B (T, N), C (T, N). Rời rạc hoá từng bước bằng discretize, quét bằng
    ssm_scan, y_t[d] = sum_n C[t, n] * h_t[d, n]. Trả (T, D).
    """
    # TODO
    raise NotImplementedError
