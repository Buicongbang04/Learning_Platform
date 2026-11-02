"""Các mảnh toán của GRPO: advantage theo nhóm, KL ước lượng k3, clipped objective, gộp loss theo token."""

from __future__ import annotations

import torch


def group_advantages(rewards: torch.Tensor, group_size: int, scale: bool = True, eps: float = 1e-4) -> torch.Tensor:
    """Advantage của từng lời giải so với nhóm của nó.

    rewards: shape (B * G,), G = group_size lời giải liên tiếp của cùng một prompt.
    scale=True: (r - mean nhóm) / (std nhóm + eps), std có hiệu chỉnh Bessel; scale=False: r - mean nhóm.
    """
    if group_size < 2 or rewards.numel() % group_size:
        raise ValueError(f"cần group_size >= 2 và chia hết {rewards.numel()} phần thưởng, nhận {group_size}")
    grouped = rewards.float().view(-1, group_size)
    centered = grouped - grouped.mean(dim=1, keepdim=True)
    if scale:
        centered = centered / (grouped.std(dim=1, keepdim=True) + eps)
    return centered.reshape(-1)


def kl_k3(logp: torch.Tensor, ref_logp: torch.Tensor) -> torch.Tensor:
    """Ước lượng k3 của KL(pi_theta || pi_ref) theo từng token, từ log-prob của token đã lấy mẫu từ pi_theta."""
    log_r = ref_logp - logp
    return torch.exp(log_r) - log_r - 1


def clipped_surrogate(logp: torch.Tensor, old_logp: torch.Tensor, advantages: torch.Tensor,
                      eps_low: float = 0.2, eps_high: float | None = None) -> torch.Tensor:
    """Objective PPO-clip theo token (cần TĂNG nó), shape (B, T). advantages shape (B,) dùng chung cho cả chuỗi."""
    eps_high = eps_low if eps_high is None else eps_high
    ratio = torch.exp(logp - old_logp)
    adv = advantages.unsqueeze(-1)
    return torch.min(ratio * adv, torch.clamp(ratio, 1 - eps_low, 1 + eps_high) * adv)


def grpo_loss(logp: torch.Tensor, old_logp: torch.Tensor, ref_logp: torch.Tensor | None, advantages: torch.Tensor,
              mask: torch.Tensor, beta: float = 0.04, eps_low: float = 0.2, eps_high: float | None = None,
              aggregation: str = "sequence") -> tuple[torch.Tensor, dict[str, float]]:
    """Loss GRPO (cần GIẢM nó) và thống kê {"kl", "clip_frac"} trên các token có mask = 1.

    aggregation="sequence": trung bình theo token trong từng chuỗi, rồi trung bình theo chuỗi (GRPO gốc).
    aggregation="token": tổng trên mọi token hợp lệ chia tổng số token hợp lệ (DAPO).
    """
    mask = mask.to(logp.dtype)
    per_token = -clipped_surrogate(logp, old_logp, advantages, eps_low, eps_high)
    kl = torch.zeros_like(logp)
    if beta != 0.0 and ref_logp is not None:
        kl = kl_k3(logp, ref_logp)
        per_token = per_token + beta * kl
    if aggregation == "sequence":
        loss = ((per_token * mask).sum(-1) / mask.sum(-1).clamp(min=1.0)).mean()
    elif aggregation == "token":
        loss = (per_token * mask).sum() / mask.sum().clamp(min=1.0)
    else:
        raise ValueError(f"aggregation phải là 'sequence' hoặc 'token', nhận {aggregation!r}")
    with torch.no_grad():
        eps_high = eps_low if eps_high is None else eps_high
        ratio = torch.exp(logp - old_logp)
        adv = advantages.unsqueeze(-1).expand_as(ratio)
        clipped = ((ratio < 1 - eps_low) & (adv < 0)) | ((ratio > 1 + eps_high) & (adv > 0))
        n = mask.sum().clamp(min=1.0)
        stats = {"kl": float((kl * mask).sum() / n), "clip_frac": float((clipped.to(mask.dtype) * mask).sum() / n)}
    return loss, stats
