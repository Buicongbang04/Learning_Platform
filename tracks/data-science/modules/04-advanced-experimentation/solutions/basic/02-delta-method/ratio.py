"""Ratio metric và delta method.

Dữ liệu ở cấp **đơn vị random** (user): num[i] là tổng tử số của user i (số click), den[i] là tổng
mẫu số (số lượt xem). Metric là tỉ số của hai tổng: R = sum(num) / sum(den).
Dùng ddof=1 cho variance và covariance.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def ratio_delta(num: np.ndarray, den: np.ndarray) -> tuple[float, float]:
    """Trả (R, var_R) với var_R tính bằng delta method.

    var_R ≈ [var(num) − 2·R·cov(num, den) + R²·var(den)] / (n · mean(den)²)
    """
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    n = len(num)
    ratio = num.sum() / den.sum()
    cov = np.cov(num, den)   # [[var(num), cov], [cov, var(den)]], ddof=1
    var = (cov[0, 0] - 2 * ratio * cov[0, 1] + ratio**2 * cov[1, 1]) / (n * den.mean() ** 2)
    return float(ratio), float(var)


def naive_binomial_se(num: np.ndarray, den: np.ndarray) -> float:
    """SE "ngây thơ": coi mỗi lượt xem là một phép thử độc lập, sqrt(R(1 − R) / sum(den))."""
    ratio = np.sum(num) / np.sum(den)
    return float(np.sqrt(ratio * (1 - ratio) / np.sum(den)))


def ratio_diff_ci(num_a, den_a, num_b, den_b, alpha: float = 0.05) -> dict:
    """Hiệu R_B − R_A, hai nhánh độc lập. Trả dict diff, se, ci_low, ci_high, p_value (z-test hai phía)."""
    ra, va = ratio_delta(num_a, den_a)
    rb, vb = ratio_delta(num_b, den_b)
    diff = rb - ra
    se = float(np.sqrt(va + vb))
    z = norm.ppf(1 - alpha / 2)
    return {
        "diff": diff, "se": se, "ci_low": diff - z * se, "ci_high": diff + z * se,
        "p_value": float(2 * norm.sf(abs(diff) / se)),
    }


def relative_lift_ci(num_a, den_a, num_b, den_b, alpha: float = 0.05) -> dict:
    """Thay đổi tương đối R_B / R_A − 1, SE bằng delta method lần nữa. Trả dict lift, se, ci_low, ci_high.

    var(R_B / R_A) ≈ var_B / R_A² + R_B² · var_A / R_A⁴
    """
    ra, va = ratio_delta(num_a, den_a)
    rb, vb = ratio_delta(num_b, den_b)
    lift = rb / ra - 1
    se = float(np.sqrt(vb / ra**2 + rb**2 * va / ra**4))
    z = norm.ppf(1 - alpha / 2)
    return {"lift": lift, "se": se, "ci_low": lift - z * se, "ci_high": lift + z * se}
