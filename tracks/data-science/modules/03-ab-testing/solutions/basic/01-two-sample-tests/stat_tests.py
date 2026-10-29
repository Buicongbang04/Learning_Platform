"""Lời giải: ba kiểm định hai mẫu."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm, t


def two_proportion_ztest(x_a: int, n_a: int, x_b: int, n_b: int) -> tuple[float, float]:
    p_a, p_b = x_a / n_a, x_b / n_b
    p_pool = (x_a + x_b) / (n_a + n_b)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    z = (p_b - p_a) / se
    return float(z), float(2 * norm.sf(abs(z)))


def diff_proportion_ci(x_a: int, n_a: int, x_b: int, n_b: int, alpha: float = 0.05) -> tuple[float, float]:
    p_a, p_b = x_a / n_a, x_b / n_b
    se = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    z = norm.ppf(1 - alpha / 2)
    diff = p_b - p_a
    return float(diff - z * se), float(diff + z * se)


def welch_ttest(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    stat = (b.mean() - a.mean()) / np.sqrt(va + vb)
    df = (va + vb) ** 2 / (va**2 / (len(a) - 1) + vb**2 / (len(b) - 1))
    return float(stat), float(2 * t.sf(abs(stat), df))
