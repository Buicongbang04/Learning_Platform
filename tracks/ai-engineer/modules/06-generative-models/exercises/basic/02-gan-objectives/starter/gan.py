"""Hàm mục tiêu của GAN, discriminator tối ưu, Jensen-Shannon, gradient penalty và đo độ phủ mode.

Discriminator trả **logit** (chưa qua sigmoid), D(x) = sigmoid(logit). Mọi loss là trung bình theo batch, để minimize.
"""

from __future__ import annotations

from typing import Callable

import torch
import torch.nn.functional as F


def d_loss(real_logits: torch.Tensor, fake_logits: torch.Tensor) -> torch.Tensor:
    """-[ mean log D(x) + mean log(1 - D(G(z))) ]: binary cross-entropy, nhãn 1 cho thật, 0 cho giả."""
    # TODO
    raise NotImplementedError


def g_loss_saturating(fake_logits: torch.Tensor) -> torch.Tensor:
    """Đúng minimax gốc: mean log(1 - D(G(z))), generator minimize."""
    # TODO
    raise NotImplementedError


def g_loss_nonsaturating(fake_logits: torch.Tensor) -> torch.Tensor:
    """Bản "non-saturating" (Goodfellow 2014, mục 3): -mean log D(G(z))."""
    # TODO
    raise NotImplementedError


def optimal_discriminator(p_data: torch.Tensor, p_g: torch.Tensor) -> torch.Tensor:
    """D*(x) = p_data / (p_data + p_g) trên từng ô của hai histogram; ô mà cả hai bằng 0 thì 0.5."""
    # TODO
    raise NotImplementedError


def js_divergence(p: torch.Tensor, q: torch.Tensor) -> torch.Tensor:
    """Jensen-Shannon divergence (nats) giữa hai phân phối rời rạc cùng shape, quy ước 0 log 0 = 0."""
    # TODO
    raise NotImplementedError


def gan_value(p_data: torch.Tensor, p_g: torch.Tensor, d: torch.Tensor) -> torch.Tensor:
    """V(D, G) = sum p_data log D + sum p_g log(1 - D) trên histogram, quy ước 0 log 0 = 0."""
    # TODO
    raise NotImplementedError


def gradient_penalty(critic: Callable[[torch.Tensor], torch.Tensor], real: torch.Tensor, fake: torch.Tensor, alpha: torch.Tensor) -> torch.Tensor:
    """WGAN-GP (Gulrajani 2017): x_hat = alpha * real + (1 - alpha) * fake, alpha shape (B,);
    trả mean (||grad_x critic(x_hat)||_2 - 1)^2, giữ graph để gradient chảy về tham số của critic.
    """
    # TODO
    raise NotImplementedError


def mode_coverage(samples: torch.Tensor, centers: torch.Tensor, std: float, min_count: int = 10) -> tuple[int, float]:
    """Đo mode collapse trên dữ liệu đồ chơi (hỗn hợp Gauss đã biết tâm), theo VEEGAN (Srivastava 2017).

    Mẫu "chất lượng cao" nằm cách tâm gần nhất dưới 3 * std. Một mode được phủ khi có ít nhất `min_count`
    mẫu chất lượng cao gán về nó. Trả (số mode được phủ, tỉ lệ mẫu chất lượng cao).
    """
    # TODO
    raise NotImplementedError
