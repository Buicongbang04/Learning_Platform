"""Hàm mục tiêu của GAN, discriminator tối ưu, Jensen-Shannon, gradient penalty và đo độ phủ mode.

Discriminator trả **logit** (chưa qua sigmoid), D(x) = sigmoid(logit). Mọi loss là trung bình theo batch, để minimize.
"""

from __future__ import annotations

from typing import Callable

import torch
import torch.nn.functional as F


def d_loss(real_logits: torch.Tensor, fake_logits: torch.Tensor) -> torch.Tensor:
    """-[ mean log D(x) + mean log(1 - D(G(z))) ]: binary cross-entropy, nhãn 1 cho thật, 0 cho giả."""
    return F.softplus(-real_logits).mean() + F.softplus(fake_logits).mean()


def g_loss_saturating(fake_logits: torch.Tensor) -> torch.Tensor:
    """Đúng minimax gốc: mean log(1 - D(G(z))), generator minimize."""
    return -F.softplus(fake_logits).mean()


def g_loss_nonsaturating(fake_logits: torch.Tensor) -> torch.Tensor:
    """Bản "non-saturating" (Goodfellow 2014, mục 3): -mean log D(G(z))."""
    return F.softplus(-fake_logits).mean()


def optimal_discriminator(p_data: torch.Tensor, p_g: torch.Tensor) -> torch.Tensor:
    """D*(x) = p_data / (p_data + p_g) trên từng ô của hai histogram; ô mà cả hai bằng 0 thì 0.5."""
    total = p_data + p_g
    return torch.where(total > 0, p_data / total.clamp_min(1e-300), torch.full_like(total, 0.5))


def js_divergence(p: torch.Tensor, q: torch.Tensor) -> torch.Tensor:
    """Jensen-Shannon divergence (nats) giữa hai phân phối rời rạc cùng shape, quy ước 0 log 0 = 0."""
    m = 0.5 * (p + q)

    def kl(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return torch.where(a > 0, a * (a.clamp_min(1e-300).log() - b.clamp_min(1e-300).log()), torch.zeros_like(a)).sum()

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def gan_value(p_data: torch.Tensor, p_g: torch.Tensor, d: torch.Tensor) -> torch.Tensor:
    """V(D, G) = sum p_data log D + sum p_g log(1 - D) trên histogram, quy ước 0 log 0 = 0."""
    a = torch.where(p_data > 0, p_data * d.clamp_min(1e-300).log(), torch.zeros_like(d))
    b = torch.where(p_g > 0, p_g * (1 - d).clamp_min(1e-300).log(), torch.zeros_like(d))
    return a.sum() + b.sum()


def gradient_penalty(critic: Callable[[torch.Tensor], torch.Tensor], real: torch.Tensor, fake: torch.Tensor, alpha: torch.Tensor) -> torch.Tensor:
    """WGAN-GP (Gulrajani 2017): x_hat = alpha * real + (1 - alpha) * fake, alpha shape (B,);
    trả mean (||grad_x critic(x_hat)||_2 - 1)^2, giữ graph để gradient chảy về tham số của critic.
    """
    a = alpha.reshape(-1, *([1] * (real.dim() - 1))).to(real.dtype)
    x_hat = (a * real + (1 - a) * fake.detach()).requires_grad_(True)
    out = critic(x_hat)
    (grad,) = torch.autograd.grad(out.sum(), x_hat, create_graph=True)
    return (grad.flatten(1).norm(dim=1) - 1).pow(2).mean()


def mode_coverage(samples: torch.Tensor, centers: torch.Tensor, std: float, min_count: int = 10) -> tuple[int, float]:
    """Đo mode collapse trên dữ liệu đồ chơi (hỗn hợp Gauss đã biết tâm), theo VEEGAN (Srivastava 2017).

    Mẫu "chất lượng cao" nằm cách tâm gần nhất dưới 3 * std. Một mode được phủ khi có ít nhất `min_count`
    mẫu chất lượng cao gán về nó. Trả (số mode được phủ, tỉ lệ mẫu chất lượng cao).
    """
    dist = torch.cdist(samples.double(), centers.double())
    nearest, idx = dist.min(dim=1)
    good = nearest < 3 * std
    counts = torch.bincount(idx[good], minlength=len(centers))
    return int((counts >= min_count).sum()), float(good.double().mean())

