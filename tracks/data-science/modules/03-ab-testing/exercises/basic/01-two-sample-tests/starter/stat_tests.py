"""Tự cài ba kiểm định hai mẫu hay dùng nhất trong A/B testing.

Được dùng numpy và scipy.stats.norm / scipy.stats.t (để lấy phân vị, CDF). Không dùng hàm kiểm định
dựng sẵn (proportions_ztest, ttest_ind...): mục tiêu là hiểu công thức.
Quy ước: mọi chênh lệch tính theo hướng B − A (treatment − control).
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm, t


def two_proportion_ztest(x_a: int, n_a: int, x_b: int, n_b: int) -> tuple[float, float]:
    """z-test hai tỉ lệ, pooled, hai phía. Trả (z, p_value), z > 0 khi p_b > p_a."""
    # TODO: p_pool = (x_a + x_b) / (n_a + n_b); se = sqrt(p_pool (1 - p_pool) (1/n_a + 1/n_b))
    raise NotImplementedError


def diff_proportion_ci(x_a: int, n_a: int, x_b: int, n_b: int, alpha: float = 0.05) -> tuple[float, float]:
    """Khoảng tin cậy Wald (không pooled) cho p_b − p_a."""
    # TODO: se = sqrt(p_a (1 - p_a) / n_a + p_b (1 - p_b) / n_b)
    raise NotImplementedError


def welch_ttest(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Welch t-test hai phía cho mean(b) − mean(a). Trả (t, p_value)."""
    # TODO: t = (mean_b - mean_a) / sqrt(var_a/n_a + var_b/n_b), var dùng ddof=1
    # TODO: bậc tự do Welch-Satterthwaite
    raise NotImplementedError
