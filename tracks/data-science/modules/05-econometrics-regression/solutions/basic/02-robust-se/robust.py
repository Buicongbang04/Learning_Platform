"""Robust (heteroskedasticity-consistent) SE và kiểm định Breusch-Pagan.

X luôn đã có cột hằng số. Được dùng numpy, scipy.stats.chi2. Không dùng cov_type= của statsmodels.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import chi2


def hc_cov(X: np.ndarray, resid: np.ndarray, kind: str = "HC3") -> np.ndarray:
    """Ma trận hiệp phương sai sandwich của beta. kind: HC0, HC1, HC3; khác thì ValueError."""
    X = np.asarray(X, dtype=float)
    resid = np.asarray(resid, dtype=float)
    n, k = X.shape
    bread = np.linalg.inv(X.T @ X)
    if kind == "HC0":
        w = np.ones(n)
    elif kind == "HC1":
        w = np.full(n, n / (n - k))
    elif kind == "HC3":
        h = ((X @ bread) * X).sum(axis=1)       # đường chéo hat matrix, không dựng ma trận n x n
        w = 1 / (1 - h) ** 2
    else:
        raise ValueError(f"kind phải là HC0, HC1 hoặc HC3, nhận {kind!r}")
    meat = (X * (w * resid**2)[:, None]).T @ X
    return bread @ meat @ bread


def robust_se(X: np.ndarray, y: np.ndarray, kind: str = "HC3") -> np.ndarray:
    """Fit OLS, trả SE robust (căn đường chéo của hc_cov)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return np.sqrt(np.diag(hc_cov(X, y - X @ beta, kind)))


def breusch_pagan(X: np.ndarray, resid: np.ndarray) -> tuple[float, float]:
    """LM = n * R² của hồi quy resid² lên X; p-value theo chi2(k - 1)."""
    X = np.asarray(X, dtype=float)
    u = np.asarray(resid, dtype=float) ** 2
    n, k = X.shape
    gamma, *_ = np.linalg.lstsq(X, u, rcond=None)
    e = u - X @ gamma
    r2 = 1 - (e @ e) / ((u - u.mean()) ** 2).sum()
    lm = n * r2
    return float(lm), float(chi2.sf(lm, k - 1))
