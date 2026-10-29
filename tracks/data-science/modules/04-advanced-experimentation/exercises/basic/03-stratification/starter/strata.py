"""Stratification: chia tầng khi random (stratified sampling) và khi phân tích (post-stratification).

strata: mảng nhãn tầng (số hoặc chuỗi), mỗi phần tử ứng với một đơn vị random.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def strata_from_quantiles(x: np.ndarray, q: int) -> np.ndarray:
    """Nhãn tầng 0..q−1 theo quantile của x (ví dụ doanh số trước thí nghiệm). Tầng q−1 là x lớn nhất."""
    # TODO: pd.qcut(..., labels=False)
    raise NotImplementedError


def stratified_assign(strata: np.ndarray, seed: int = 0) -> np.ndarray:
    """Mảng bool (True = treatment). Trong MỖI tầng, số treatment và control lệch nhau tối đa 1.

    Thứ tự trong tầng ngẫu nhiên; tầng có số lẻ đơn vị thì nhánh nhận đơn vị thừa cũng ngẫu nhiên.
    Dùng np.random.default_rng(seed).
    """
    # TODO
    raise NotImplementedError


def post_stratified_effect(y: np.ndarray, treat: np.ndarray, strata: np.ndarray, alpha: float = 0.05) -> dict:
    """Ước lượng post-stratified: tổng theo tầng của w_k · (mean_T,k − mean_C,k), w_k = N_k / N.

    SE² = tổng w_k² · (s²_T,k / n_T,k + s²_C,k / n_C,k), ddof=1.
    Trả dict diff, se, ci_low, ci_high. ValueError nếu một tầng có dưới 2 đơn vị ở một nhánh.
    """
    # TODO
    raise NotImplementedError
