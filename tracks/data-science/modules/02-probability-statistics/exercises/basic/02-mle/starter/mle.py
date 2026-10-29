"""Tự viết Maximum Likelihood Estimation (MLE) cho các phân phối hay gặp.

Được dùng numpy và scipy.optimize.minimize. Không dùng scipy.stats.*.fit hay logpdf: test sẽ so kết quả
của bạn với chúng.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


def bernoulli_mle(x: np.ndarray) -> float:
    """MLE của p cho dữ liệu 0/1 (đơn trễ hay không)."""
    # TODO
    raise NotImplementedError


def poisson_mle(x: np.ndarray) -> float:
    """MLE của lambda cho dữ liệu đếm (số đơn mỗi giờ)."""
    # TODO
    raise NotImplementedError


def exponential_mle(x: np.ndarray) -> float:
    """MLE của **rate** lambda (không phải scale = 1/lambda) cho Exponential."""
    # TODO
    raise NotImplementedError


def lognormal_mle(x: np.ndarray) -> tuple[float, float]:
    """MLE dạng đóng (mu, sigma) cho Lognormal: tham số của log(x), sigma dùng ddof=0."""
    # TODO
    raise NotImplementedError


def lognormal_nll(mu: float, sigma: float, x: np.ndarray) -> float:
    """Negative log-likelihood của Lognormal(mu, sigma) trên dữ liệu x (tổng, không phải trung bình).

    log f(x) = -log(x) - log(sigma) - 0.5 log(2 pi) - (log(x) - mu)^2 / (2 sigma^2)
    """
    # TODO
    raise NotImplementedError


def fit_lognormal_numeric(x: np.ndarray) -> tuple[float, float]:
    """Tìm (mu, sigma) bằng cách cực tiểu lognormal_nll với scipy.optimize.minimize.

    Tối ưu theo (mu, log_sigma) để sigma luôn dương; khởi đầu từ (0, 0) cũng phải hội tụ.
    """
    # TODO
    raise NotImplementedError
