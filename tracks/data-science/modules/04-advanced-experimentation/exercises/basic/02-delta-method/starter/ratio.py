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
    # TODO
    raise NotImplementedError


def naive_binomial_se(num: np.ndarray, den: np.ndarray) -> float:
    """SE "ngây thơ": coi mỗi lượt xem là một phép thử độc lập, sqrt(R(1 − R) / sum(den))."""
    # TODO
    raise NotImplementedError


def ratio_diff_ci(num_a, den_a, num_b, den_b, alpha: float = 0.05) -> dict:
    """Hiệu R_B − R_A, hai nhánh độc lập. Trả dict diff, se, ci_low, ci_high, p_value (z-test hai phía)."""
    # TODO
    raise NotImplementedError


def relative_lift_ci(num_a, den_a, num_b, den_b, alpha: float = 0.05) -> dict:
    """Thay đổi tương đối R_B / R_A − 1, SE bằng delta method lần nữa. Trả dict lift, se, ci_low, ci_high.

    var(R_B / R_A) ≈ var_B / R_A² + R_B² · var_A / R_A⁴
    """
    # TODO
    raise NotImplementedError
