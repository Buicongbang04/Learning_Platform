"""Regression Discontinuity (sharp): local linear, độ nhạy theo bandwidth, kiểm tra manipulation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import binomtest


def rdd_estimate(x: np.ndarray, y: np.ndarray, cutoff: float, bandwidth: float) -> tuple[float, float]:
    """Bước nhảy của E[y | x] tại cutoff, ước lượng local linear với kernel tam giác."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    r = x - cutoff
    keep = np.abs(r) < bandwidth
    r, yk = r[keep], y[keep]
    d = (r >= 0).astype(float)
    X = np.column_stack([np.ones_like(r), d, r, d * r])
    w = 1 - np.abs(r) / bandwidth
    fit = sm.WLS(yk, X, weights=w).fit(cov_type="HC1")
    return float(fit.params[1]), float(fit.bse[1])


def bandwidth_sensitivity(x: np.ndarray, y: np.ndarray, cutoff: float,
                          bandwidths: list[float]) -> pd.DataFrame:
    """Một dòng mỗi bandwidth: bandwidth, estimate, se, n (số quan sát trong cửa sổ)."""
    r = np.asarray(x, dtype=float) - cutoff
    rows = []
    for h in bandwidths:
        est, se = rdd_estimate(x, y, cutoff, h)
        rows.append({"bandwidth": h, "estimate": est, "se": se, "n": int((np.abs(r) < h).sum())})
    return pd.DataFrame(rows, columns=["bandwidth", "estimate", "se", "n"])


def density_check(x: np.ndarray, cutoff: float, width: float) -> float:
    """p-value hai phía: số quan sát trong [cutoff − width, cutoff) so với [cutoff, cutoff + width)."""
    r = np.asarray(x, dtype=float) - cutoff
    left = int(((r >= -width) & (r < 0)).sum())
    right = int(((r >= 0) & (r < width)).sum())
    return float(binomtest(right, left + right, 0.5).pvalue)
