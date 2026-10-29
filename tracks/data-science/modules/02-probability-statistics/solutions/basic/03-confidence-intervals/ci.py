"""Khoảng tin cậy cho trung bình và cho tỉ lệ, và kiểm tra độ phủ (coverage) bằng mô phỏng.

Được dùng numpy, scipy.stats.t và scipy.stats.norm (để lấy phân vị). Không dùng hàm dựng sẵn
(scipy.stats.t.interval, statsmodels proportion_confint): test so kết quả của bạn với chúng.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.stats import norm, t


def mean_ci(x: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    """Khoảng tin cậy t cho trung bình: mean ± t_{1-alpha/2, n-1} * s / sqrt(n), s dùng ddof=1."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    half = t.ppf(1 - alpha / 2, n - 1) * x.std(ddof=1) / np.sqrt(n)
    return float(x.mean() - half), float(x.mean() + half)


def wald_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wald: p_hat ± z * sqrt(p_hat (1 - p_hat) / n). Cắt hai đầu về [0, 1] (giống statsmodels)."""
    p = k / n
    half = norm.ppf(1 - alpha / 2) * np.sqrt(p * (1 - p) / n)
    return float(max(p - half, 0.0)), float(min(p + half, 1.0))


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval (công thức trong README của bài)."""
    z = norm.ppf(1 - alpha / 2)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return float(center - half), float(center + half)


def coverage(ci_fn: Callable[[int, int, float], tuple[float, float]], p: float, n: int,
             n_sims: int = 10000, seed: int = 0, alpha: float = 0.05) -> float:
    """Tỉ lệ khoảng tin cậy chứa p thật, qua n_sims lần mô phỏng k ~ Binomial(n, p).

    Dùng np.random.default_rng(seed). Khoảng chứa p khi lo <= p <= hi.
    """
    ks = np.random.default_rng(seed).binomial(n, p, n_sims)
    # k chỉ nhận tối đa n + 1 giá trị: tính khoảng một lần cho mỗi giá trị rồi đếm
    values, counts = np.unique(ks, return_counts=True)
    hit = 0
    for k, c in zip(values, counts):
        lo, hi = ci_fn(int(k), n, alpha)
        hit += c * (lo <= p <= hi)
    return float(hit / n_sims)
