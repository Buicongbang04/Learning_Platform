"""OLS bằng ma trận: tự tính hệ số, SE, t, p-value, R².

Được dùng numpy và scipy.stats.t. Không dùng statsmodels: mục tiêu là hiểu từng con số trong
bảng summary().
"""

from __future__ import annotations

import numpy as np
from scipy.stats import t


def add_intercept(X: np.ndarray) -> np.ndarray:
    """Thêm cột 1 vào đầu X. X 1 chiều được coi như một cột."""
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    return np.column_stack([np.ones(len(X)), X])


def ols_fit(X: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray | float]:
    """OLS với X đã có cột hằng số.

    Trả dict: beta, resid, sigma2, se, t, p, r2, adj_r2. Raise ValueError nếu X thiếu rank cột.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, k = X.shape
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    if rank < k:
        raise ValueError(f"X thiếu rank cột: rank {rank} < {k} cột (có cột là tổ hợp tuyến tính của cột khác)")
    resid = y - X @ beta
    df = n - k
    ssr = resid @ resid
    sigma2 = ssr / df
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
    t_stat = beta / se
    sst = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ssr / sst
    return {
        "beta": beta,
        "resid": resid,
        "sigma2": float(sigma2),
        "se": se,
        "t": t_stat,
        "p": 2 * t.sf(np.abs(t_stat), df),
        "r2": float(r2),
        "adj_r2": float(1 - (1 - r2) * (n - 1) / df),
    }
