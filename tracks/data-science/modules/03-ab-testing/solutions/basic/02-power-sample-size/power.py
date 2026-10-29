"""Lời giải: power, MDE và cỡ mẫu."""

from __future__ import annotations

import math

from scipy.optimize import brentq
from scipy.stats import norm


def _z(alpha: float, power: float) -> float:
    return norm.ppf(1 - alpha / 2) + norm.ppf(power)


def _n_exact(p_baseline: float, mde_abs: float, alpha: float, power: float) -> float:
    p1, p2 = p_baseline, p_baseline + mde_abs
    return _z(alpha, power) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / mde_abs**2


def sample_size_proportions(p_baseline: float, mde_abs: float, alpha: float = 0.05, power: float = 0.8) -> int:
    return math.ceil(_n_exact(p_baseline, mde_abs, alpha, power))


def mde_proportions(p_baseline: float, n_per_group: int, alpha: float = 0.05, power: float = 0.8) -> float:
    return brentq(lambda m: _n_exact(p_baseline, m, alpha, power) - n_per_group, 1e-6, 1 - p_baseline - 1e-9)


def sample_size_means(sigma: float, mde_abs: float, alpha: float = 0.05, power: float = 0.8) -> int:
    return math.ceil(2 * sigma**2 * _z(alpha, power) ** 2 / mde_abs**2)
