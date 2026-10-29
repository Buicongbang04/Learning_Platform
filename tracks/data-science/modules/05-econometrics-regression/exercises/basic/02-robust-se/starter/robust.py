"""Robust (heteroskedasticity-consistent) SE và kiểm định Breusch-Pagan.

X luôn đã có cột hằng số. Được dùng numpy, scipy.stats.chi2. Không dùng cov_type= của statsmodels.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import chi2


def hc_cov(X: np.ndarray, resid: np.ndarray, kind: str = "HC3") -> np.ndarray:
    """Ma trận hiệp phương sai sandwich của beta. kind: HC0, HC1, HC3; khác thì ValueError."""
    # TODO: bread = inv(X'X)
    # TODO: trọng số w theo kind (HC3 cần đường chéo hat matrix, đừng dựng ma trận n x n)
    # TODO: meat = sum_i w_i e_i^2 x_i x_i'; trả bread @ meat @ bread
    raise NotImplementedError


def robust_se(X: np.ndarray, y: np.ndarray, kind: str = "HC3") -> np.ndarray:
    """Fit OLS, trả SE robust (căn đường chéo của hc_cov)."""
    # TODO
    raise NotImplementedError


def breusch_pagan(X: np.ndarray, resid: np.ndarray) -> tuple[float, float]:
    """LM = n * R² của hồi quy resid² lên X; p-value theo chi2(k - 1)."""
    # TODO
    raise NotImplementedError
