"""Tự tính xác suất từ các phân phối hay gặp trong vận hành e-commerce.

Chỉ dùng thư viện chuẩn `math` và `numpy`. Không dùng scipy.stats (test sẽ so kết quả với scipy).
"""

from __future__ import annotations

import math

import numpy as np


def binom_pmf(k: int, n: int, p: float) -> float:
    """P(X = k) với X ~ Binomial(n, p): số đơn trễ trong n đơn, mỗi đơn trễ độc lập với xác suất p."""
    if k < 0 or k > n:
        return 0.0
    return math.comb(n, k) * p**k * (1 - p) ** (n - k)


def prob_at_least(k: int, n: int, p: float) -> float:
    """P(X >= k) với X ~ Binomial(n, p)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    # Cộng phía đuôi trực tiếp thay vì 1 - cdf: tránh mất chữ số khi kết quả rất nhỏ
    return sum(binom_pmf(i, n, p) for i in range(k, n + 1))


def poisson_pmf(k: int, lam: float) -> float:
    """P(N = k) với N ~ Poisson(lam): số đơn đến trong một giờ khi trung bình là lam đơn/giờ.

    Phải chạy đúng cả khi lam và k lớn (lam = 250, k = 300): lam**k và k! đều tràn số thực.
    """
    if k < 0:
        return 0.0
    return math.exp(k * math.log(lam) - lam - math.lgamma(k + 1))


def lognormal_from_mean_median(mean: float, median: float) -> tuple[float, float]:
    """Tham số (mu, sigma) của Lognormal có đúng mean và median cho trước.

    Với X = exp(Y), Y ~ Normal(mu, sigma): median = exp(mu), mean = exp(mu + sigma^2 / 2).
    Lognormal luôn có mean > median; nếu mean <= median thì raise ValueError.
    """
    if mean <= median or median <= 0:
        raise ValueError("Lognormal cần mean > median > 0")
    mu = math.log(median)
    sigma = math.sqrt(2 * (math.log(mean) - mu))
    return mu, sigma


def dispersion_index(counts: np.ndarray) -> float:
    """Tỉ số variance / mean của dữ liệu đếm (variance mẫu, ddof=1). Poisson cho giá trị gần 1."""
    counts = np.asarray(counts, dtype=float)
    return float(counts.var(ddof=1) / counts.mean())
