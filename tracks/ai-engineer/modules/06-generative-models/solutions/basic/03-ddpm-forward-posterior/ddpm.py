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
    return torch.linspace(beta_start, beta_end, T, dtype=torch.float64)


def cosine_betas(T: int = 1000, s: float = 0.008, max_beta: float = 0.999) -> torch.Tensor:
    """Schedule cosine của Nichol & Dhariwal (2021).

    f(u) = cos^2(((u / T) + s) / (1 + s) * pi / 2), alpha_bar(u) = f(u) / f(0) với u = 0..T,
    beta[t] = 1 - alpha_bar(t + 1) / alpha_bar(t), chặn trên ở max_beta. Trả float64 shape (T,).
    """
    u = torch.arange(T + 1, dtype=torch.float64)
    f = torch.cos(((u / T) + s) / (1 + s) * math.pi / 2) ** 2
    abar = f / f[0]
    return (1 - abar[1:] / abar[:-1]).clamp(max=max_beta)


def alpha_bars(betas: torch.Tensor) -> torch.Tensor:
    """alpha_bar[t] = prod_{s <= t} (1 - betas[s])."""
    return torch.cumprod(1 - betas, dim=0)


def _gather(values: torch.Tensor, t: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """values[t] đổi shape thành (B, 1, 1, ...) để nhân với x (B, ...), cùng dtype và device với x."""
    out = values.to(x.device)[t].to(x.dtype)
    return out.reshape(-1, *([1] * (x.dim() - 1)))


def q_sample(x0: torch.Tensor, t: torch.Tensor, noise: torch.Tensor, alpha_bar: torch.Tensor) -> torch.Tensor:
    """x_t = sqrt(alpha_bar[t]) * x0 + sqrt(1 - alpha_bar[t]) * noise, t shape (B,) mỗi mẫu một bước."""
    ab = _gather(alpha_bar, t, x0)
    return ab.sqrt() * x0 + (1 - ab).sqrt() * noise


def q_posterior(x0: torch.Tensor, xt: torch.Tensor, t: torch.Tensor, betas: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Mean và variance của q(x_{t-1} | x_t, x_0); variance shape (B, 1, ...), bằng 0 tại t = 0."""
    abar = alpha_bars(betas)
    abar_prev = torch.cat([abar.new_ones(1), abar[:-1]])
    beta_t = _gather(betas, t, x0)
    ab_t = _gather(abar, t, x0)
    ab_prev = _gather(abar_prev, t, x0)
    alpha_t = 1 - beta_t
    coef_x0 = ab_prev.sqrt() * beta_t / (1 - ab_t)
    coef_xt = alpha_t.sqrt() * (1 - ab_prev) / (1 - ab_t)
    var = beta_t * (1 - ab_prev) / (1 - ab_t)
    return coef_x0 * x0 + coef_xt * xt, var


def predict_x0(xt: torch.Tensor, t: torch.Tensor, eps: torch.Tensor, alpha_bar: torch.Tensor) -> torch.Tensor:
    """Đảo q_sample: x0 = (x_t - sqrt(1 - alpha_bar[t]) * eps) / sqrt(alpha_bar[t])."""
    ab = _gather(alpha_bar, t, xt)
    return (xt - (1 - ab).sqrt() * eps) / ab.sqrt()


def p_mean_variance(xt: torch.Tensor, t: torch.Tensor, eps: torch.Tensor, betas: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Mean và variance của p(x_{t-1} | x_t) khi model dự đoán nhiễu eps.

    mean = (x_t - beta_t / sqrt(1 - alpha_bar[t]) * eps) / sqrt(1 - beta_t); variance là variance của posterior
    (beta tilde, "fixed small" trong bài báo), bằng 0 tại t = 0.
    """
    abar = alpha_bars(betas)
    abar_prev = torch.cat([abar.new_ones(1), abar[:-1]])
    beta_t = _gather(betas, t, xt)
    ab_t = _gather(abar, t, xt)
    ab_prev = _gather(abar_prev, t, xt)
    mean = (xt - beta_t / (1 - ab_t).sqrt() * eps) / (1 - beta_t).sqrt()
    return mean, beta_t * (1 - ab_prev) / (1 - ab_t)


def snr(alpha_bar: torch.Tensor) -> torch.Tensor:
    """Signal-to-noise ratio alpha_bar / (1 - alpha_bar)."""
    return alpha_bar / (1 - alpha_bar)
