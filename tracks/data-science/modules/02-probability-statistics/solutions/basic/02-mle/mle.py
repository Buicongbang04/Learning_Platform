"""Tự viết Maximum Likelihood Estimation (MLE) cho các phân phối hay gặp.

Được dùng numpy và scipy.optimize.minimize. Không dùng scipy.stats.*.fit hay logpdf: test sẽ so kết quả
của bạn với chúng.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


def bernoulli_mle(x: np.ndarray) -> float:
    """MLE của p cho dữ liệu 0/1 (đơn trễ hay không)."""
    return float(np.mean(x))


def poisson_mle(x: np.ndarray) -> float:
    """MLE của lambda cho dữ liệu đếm (số đơn mỗi giờ)."""
    return float(np.mean(x))


def exponential_mle(x: np.ndarray) -> float:
    """MLE của **rate** lambda (không phải scale = 1/lambda) cho Exponential."""
    return float(1.0 / np.mean(x))


def lognormal_mle(x: np.ndarray) -> tuple[float, float]:
    """MLE dạng đóng (mu, sigma) cho Lognormal: tham số của log(x), sigma dùng ddof=0."""
    y = np.log(np.asarray(x, dtype=float))
    return float(y.mean()), float(y.std(ddof=0))


def lognormal_nll(mu: float, sigma: float, x: np.ndarray) -> float:
    """Negative log-likelihood của Lognormal(mu, sigma) trên dữ liệu x (tổng, không phải trung bình).

    log f(x) = -log(x) - log(sigma) - 0.5 log(2 pi) - (log(x) - mu)^2 / (2 sigma^2)
    """
    y = np.log(np.asarray(x, dtype=float))
    logpdf = -y - np.log(sigma) - 0.5 * np.log(2 * np.pi) - (y - mu) ** 2 / (2 * sigma**2)
    return float(-logpdf.sum())


def fit_lognormal_numeric(x: np.ndarray) -> tuple[float, float]:
    """Tìm (mu, sigma) bằng cách cực tiểu lognormal_nll với scipy.optimize.minimize.

    Tối ưu theo (mu, log_sigma) để sigma luôn dương; khởi đầu từ (0, 0) cũng phải hội tụ.
    """
    n = len(x)

    def objective(theta: np.ndarray) -> float:
        # chia cho n: hàm mục tiêu cỡ O(1) giúp optimizer hội tụ ổn định hơn
        return lognormal_nll(theta[0], np.exp(theta[1]), x) / n

    result = minimize(objective, x0=np.zeros(2), method="BFGS")
    return float(result.x[0]), float(np.exp(result.x[1]))
