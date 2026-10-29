"""CUPED (Controlled-experiment Using Pre-Experiment Data) tự viết bằng numpy.

y: metric trong thí nghiệm, x: cùng metric (hoặc metric tương quan) đo TRƯỚC thí nghiệm,
treat: mảng bool, True là nhánh treatment. Dùng ddof=1 cho variance và covariance.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm


def cuped_theta(y: np.ndarray, x: np.ndarray) -> float:
    """theta = cov(y, x) / var(x)."""
    # TODO
    raise NotImplementedError


def cuped_adjust(y: np.ndarray, x: np.ndarray, theta: float | None = None) -> np.ndarray:
    """y_cuped = y − theta · (x − mean(x)). theta=None thì tự tính bằng cuped_theta."""
    # TODO
    raise NotImplementedError


def variance_reduction(y: np.ndarray, x: np.ndarray) -> float:
    """Tỉ lệ variance giảm được: 1 − var(y_cuped) / var(y)."""
    # TODO
    raise NotImplementedError


def cuped_effect(y: np.ndarray, x: np.ndarray, treat: np.ndarray, alpha: float = 0.05) -> dict:
    """Ước lượng tác động có và không có CUPED.

    theta tính trên dữ liệu gộp cả hai nhánh. Trả dict:
    diff, se, ci_low, ci_high (trên y_cuped) và diff_raw, se_raw (trên y gốc).
    SE theo công thức Welch: sqrt(s²_T / n_T + s²_C / n_C).
    """
    # TODO
    raise NotImplementedError


def n_after_cuped(n: int, rho: float) -> int:
    """Cỡ mẫu cần sau CUPED để giữ nguyên power: n · (1 − rho²), làm tròn lên."""
    # TODO
    raise NotImplementedError
