"""Các mảnh toán của GRPO: advantage theo nhóm, KL ước lượng k3, clipped objective, gộp loss theo token."""

from __future__ import annotations

import torch


def group_advantages(rewards: torch.Tensor, group_size: int, scale: bool = True, eps: float = 1e-4) -> torch.Tensor:
    """Advantage của từng lời giải so với nhóm của nó.

    rewards: shape (B * G,), G = group_size lời giải liên tiếp của cùng một prompt.
    scale=True: (r - mean nhóm) / (std nhóm + eps), std có hiệu chỉnh Bessel; scale=False: r - mean nhóm.
    """
    # TODO
    raise NotImplementedError


def kl_k3(logp: torch.Tensor, ref_logp: torch.Tensor) -> torch.Tensor:
    """Ước lượng k3 của KL(pi_theta || pi_ref) theo từng token, từ log-prob của token đã lấy mẫu từ pi_theta."""
    # TODO
    raise NotImplementedError


def clipped_surrogate(logp: torch.Tensor, old_logp: torch.Tensor, advantages: torch.Tensor,
                      eps_low: float = 0.2, eps_high: float | None = None) -> torch.Tensor:
    """Objective PPO-clip theo token (cần TĂNG nó), shape (B, T). advantages shape (B,) dùng chung cho cả chuỗi."""
    # TODO
    raise NotImplementedError


def grpo_loss(logp: torch.Tensor, old_logp: torch.Tensor, ref_logp: torch.Tensor | None, advantages: torch.Tensor,
              mask: torch.Tensor, beta: float = 0.04, eps_low: float = 0.2, eps_high: float | None = None,
              aggregation: str = "sequence") -> tuple[torch.Tensor, dict[str, float]]:
    """Loss GRPO (cần GIẢM nó) và thống kê {"kl", "clip_frac"} trên các token có mask = 1.

    aggregation="sequence": trung bình theo token trong từng chuỗi, rồi trung bình theo chuỗi (GRPO gốc).
    aggregation="token": tổng trên mọi token hợp lệ chia tổng số token hợp lệ (DAPO).
    """
    # TODO
    raise NotImplementedError
