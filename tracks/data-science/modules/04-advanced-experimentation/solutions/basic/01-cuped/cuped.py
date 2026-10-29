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
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    return float(np.cov(y, x)[0, 1] / np.var(x, ddof=1))


def cuped_adjust(y: np.ndarray, x: np.ndarray, theta: float | None = None) -> np.ndarray:
    """y_cuped = y − theta · (x − mean(x)). theta=None thì tự tính bằng cuped_theta."""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    if theta is None:
        theta = cuped_theta(y, x)
    return y - theta * (x - x.mean())


def variance_reduction(y: np.ndarray, x: np.ndarray) -> float:
    """Tỉ lệ variance giảm được: 1 − var(y_cuped) / var(y)."""
    y = np.asarray(y, dtype=float)
    return float(1 - cuped_adjust(y, x).var(ddof=1) / y.var(ddof=1))


def _diff_se(v: np.ndarray, treat: np.ndarray) -> tuple[float, float]:
    a, b = v[~treat], v[treat]
    return float(b.mean() - a.mean()), float(np.sqrt(b.var(ddof=1) / len(b) + a.var(ddof=1) / len(a)))


def cuped_effect(y: np.ndarray, x: np.ndarray, treat: np.ndarray, alpha: float = 0.05) -> dict:
    """Ước lượng tác động có và không có CUPED.

    theta tính trên dữ liệu gộp cả hai nhánh. Trả dict:
    diff, se, ci_low, ci_high (trên y_cuped) và diff_raw, se_raw (trên y gốc).
    SE theo công thức Welch: sqrt(s²_T / n_T + s²_C / n_C).
    """
    y = np.asarray(y, dtype=float)
    treat = np.asarray(treat, dtype=bool)
    diff_raw, se_raw = _diff_se(y, treat)
    diff, se = _diff_se(cuped_adjust(y, x), treat)
    z = norm.ppf(1 - alpha / 2)
    return {
        "diff": diff, "se": se, "ci_low": diff - z * se, "ci_high": diff + z * se,
        "diff_raw": diff_raw, "se_raw": se_raw,
    }


def n_after_cuped(n: int, rho: float) -> int:
    """Cỡ mẫu cần sau CUPED để giữ nguyên power: n · (1 − rho²), làm tròn lên."""
    return int(math.ceil(n * (1 - rho**2) - 1e-9))
