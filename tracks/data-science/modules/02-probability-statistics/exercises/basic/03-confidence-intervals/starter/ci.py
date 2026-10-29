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
    # TODO
    raise NotImplementedError


def wald_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wald: p_hat ± z * sqrt(p_hat (1 - p_hat) / n). Cắt hai đầu về [0, 1] (giống statsmodels)."""
    # TODO
    raise NotImplementedError


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval (công thức trong README của bài)."""
    # TODO
    raise NotImplementedError


def coverage(ci_fn: Callable[[int, int, float], tuple[float, float]], p: float, n: int,
             n_sims: int = 10000, seed: int = 0, alpha: float = 0.05) -> float:
    """Tỉ lệ khoảng tin cậy chứa p thật, qua n_sims lần mô phỏng k ~ Binomial(n, p).

    Dùng np.random.default_rng(seed). Khoảng chứa p khi lo <= p <= hi.
    """
    # TODO
    raise NotImplementedError
