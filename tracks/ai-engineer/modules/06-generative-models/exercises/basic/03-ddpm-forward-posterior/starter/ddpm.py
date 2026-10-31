"""DDPM: noise schedule, forward process q(x_t | x_0) dạng đóng và posterior q(x_{t-1} | x_t, x_0).

Quy ước chỉ số: mảng dài T, chỉ số t = 0..T-1 ứng với bước t + 1 trong bài báo DDPM. alpha_bar[t] là tích
(1 - beta_s) với s = 0..t. "alpha_bar trước bước 0" bằng 1 (x_0 là dữ liệu sạch).
Mọi hàm nhận tensor torch; schedule dùng float64.
"""

from __future__ import annotations

import math

import torch


def linear_betas(T: int = 1000, beta_start: float = 1e-4, beta_end: float = 0.02) -> torch.Tensor:
    """Schedule tuyến tính của Ho et al. (2020): T giá trị cách đều từ beta_start tới beta_end, float64."""
    # TODO
    raise NotImplementedError


def cosine_betas(T: int = 1000, s: float = 0.008, max_beta: float = 0.999) -> torch.Tensor:
    """Schedule cosine của Nichol & Dhariwal (2021).

    f(u) = cos^2(((u / T) + s) / (1 + s) * pi / 2), alpha_bar(u) = f(u) / f(0) với u = 0..T,
    beta[t] = 1 - alpha_bar(t + 1) / alpha_bar(t), chặn trên ở max_beta. Trả float64 shape (T,).
    """
    # TODO
    raise NotImplementedError


def alpha_bars(betas: torch.Tensor) -> torch.Tensor:
    """alpha_bar[t] = prod_{s <= t} (1 - betas[s])."""
    # TODO
    raise NotImplementedError


def q_sample(x0: torch.Tensor, t: torch.Tensor, noise: torch.Tensor, alpha_bar: torch.Tensor) -> torch.Tensor:
    """x_t = sqrt(alpha_bar[t]) * x0 + sqrt(1 - alpha_bar[t]) * noise, t shape (B,) mỗi mẫu một bước."""
    # TODO
    raise NotImplementedError


def q_posterior(x0: torch.Tensor, xt: torch.Tensor, t: torch.Tensor, betas: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Mean và variance của q(x_{t-1} | x_t, x_0); variance shape (B, 1, ...), bằng 0 tại t = 0."""
    # TODO
    raise NotImplementedError


def predict_x0(xt: torch.Tensor, t: torch.Tensor, eps: torch.Tensor, alpha_bar: torch.Tensor) -> torch.Tensor:
    """Đảo q_sample: x0 = (x_t - sqrt(1 - alpha_bar[t]) * eps) / sqrt(alpha_bar[t])."""
    # TODO
    raise NotImplementedError


def p_mean_variance(xt: torch.Tensor, t: torch.Tensor, eps: torch.Tensor, betas: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Mean và variance của p(x_{t-1} | x_t) khi model dự đoán nhiễu eps.

    mean = (x_t - beta_t / sqrt(1 - alpha_bar[t]) * eps) / sqrt(1 - beta_t); variance là variance của posterior
    (beta tilde, "fixed small" trong bài báo), bằng 0 tại t = 0.
    """
    # TODO
    raise NotImplementedError


def snr(alpha_bar: torch.Tensor) -> torch.Tensor:
    """Signal-to-noise ratio alpha_bar / (1 - alpha_bar)."""
    # TODO
    raise NotImplementedError
