"""Regression Discontinuity (sharp): local linear, độ nhạy theo bandwidth, kiểm tra manipulation.

Quy ước: đơn vị có x >= cutoff được can thiệp (sharp RDD). Bước nhảy tính theo hướng phải − trái.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import binomtest


def rdd_estimate(x: np.ndarray, y: np.ndarray, cutoff: float, bandwidth: float) -> tuple[float, float]:
    """Bước nhảy của E[y | x] tại cutoff, ước lượng local linear với kernel tam giác.

    - Chỉ dùng quan sát có |x − cutoff| < bandwidth.
    - r = x − cutoff, d = 1 nếu r >= 0. Hồi quy WLS y ~ 1 + d + r + d·r (slope riêng mỗi bên),
      trọng số w = 1 − |r| / bandwidth, standard error HC1.
    - Trả (hệ số của d, SE của nó).
    """
    # TODO
    raise NotImplementedError


def bandwidth_sensitivity(x: np.ndarray, y: np.ndarray, cutoff: float,
                          bandwidths: list[float]) -> pd.DataFrame:
    """DataFrame cột đúng thứ tự bandwidth, estimate, se, n (số quan sát trong cửa sổ), một dòng mỗi bandwidth."""
    # TODO: gọi rdd_estimate cho từng bandwidth
    raise NotImplementedError


def density_check(x: np.ndarray, cutoff: float, width: float) -> float:
    """Kiểm tra manipulation đơn giản: nếu không ai "chen" qua ngưỡng, số quan sát ngay bên trái
    [cutoff − width, cutoff) và ngay bên phải [cutoff, cutoff + width) xấp xỉ bằng nhau.

    Trả p-value hai phía của binomial test: số bên phải trên tổng hai bên, xác suất 0.5.
    """
    # TODO: scipy.stats.binomtest
    raise NotImplementedError
