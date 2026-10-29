"""Tự tính xác suất từ các phân phối hay gặp trong vận hành e-commerce.

Chỉ dùng thư viện chuẩn `math` và `numpy`. Không dùng scipy.stats (test sẽ so kết quả với scipy).
"""

from __future__ import annotations

import math

import numpy as np


def binom_pmf(k: int, n: int, p: float) -> float:
    """P(X = k) với X ~ Binomial(n, p): số đơn trễ trong n đơn, mỗi đơn trễ độc lập với xác suất p."""
    # TODO: C(n, k) p^k (1 - p)^(n - k), dùng math.comb
    raise NotImplementedError


def prob_at_least(k: int, n: int, p: float) -> float:
    """P(X >= k) với X ~ Binomial(n, p)."""
    # TODO: 1 - P(X <= k - 1); với k <= 0 thì xác suất là 1
    raise NotImplementedError


def poisson_pmf(k: int, lam: float) -> float:
    """P(N = k) với N ~ Poisson(lam): số đơn đến trong một giờ khi trung bình là lam đơn/giờ.

    Phải chạy đúng cả khi lam và k lớn (lam = 250, k = 300): lam**k và k! đều tràn số thực.
    """
    # TODO: tính log pmf = k log(lam) - lam - log(k!) (math.lgamma(k + 1) = log(k!)), rồi exp
    raise NotImplementedError


def lognormal_from_mean_median(mean: float, median: float) -> tuple[float, float]:
    """Tham số (mu, sigma) của Lognormal có đúng mean và median cho trước.

    Với X = exp(Y), Y ~ Normal(mu, sigma): median = exp(mu), mean = exp(mu + sigma^2 / 2).
    Lognormal luôn có mean > median; nếu mean <= median thì raise ValueError.
    """
    # TODO
    raise NotImplementedError


def dispersion_index(counts: np.ndarray) -> float:
    """Tỉ số variance / mean của dữ liệu đếm (variance mẫu, ddof=1). Poisson cho giá trị gần 1."""
    # TODO
    raise NotImplementedError
