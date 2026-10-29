"""OLS bằng ma trận: tự tính hệ số, SE, t, p-value, R².

Được dùng numpy và scipy.stats.t. Không dùng statsmodels: mục tiêu là hiểu từng con số trong
bảng summary().
"""

from __future__ import annotations

import numpy as np
from scipy.stats import t


def add_intercept(X: np.ndarray) -> np.ndarray:
    """Thêm cột 1 vào đầu X. X 1 chiều được coi như một cột."""
    # TODO: np.column_stack([np.ones(n), X])
    raise NotImplementedError


def ols_fit(X: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray | float]:
    """OLS với X đã có cột hằng số.

    Trả dict: beta, resid, sigma2, se, t, p, r2, adj_r2. Raise ValueError nếu X thiếu rank cột.
    """
    # TODO: beta, rank từ np.linalg.lstsq; rank < số cột -> ValueError
    # TODO: resid, sigma2 = SSR / (n - k), se = sqrt(diag(sigma2 * inv(X'X)))
    # TODO: t = beta / se, p hai phía theo t(n - k); r2 và adj_r2
    raise NotImplementedError
