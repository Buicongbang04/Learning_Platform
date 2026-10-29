"""Target encoding có smoothing và phiên bản out-of-fold cho tập train."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold


def fit_target_encoding(categories: pd.Series, y, smoothing: float = 20.0) -> tuple[pd.Series, float]:
    """Học bảng mã hoá: (mapping, prior).

    prior = trung bình y. Với mỗi category c có n_c dòng và tổng nhãn s_c:
        mapping[c] = (s_c + smoothing · prior) / (n_c + smoothing)
    NaN trong categories không được học (sẽ nhận prior khi transform).
    """
    # TODO: groupby category, lấy sum và count của y
    raise NotImplementedError


def transform_target_encoding(categories: pd.Series, mapping: pd.Series, prior: float) -> np.ndarray:
    """Tra bảng; category chưa gặp hoặc NaN nhận prior."""
    # TODO
    raise NotImplementedError


def oof_target_encoding(categories: pd.Series, y, n_splits: int = 5, smoothing: float = 20.0,
                        seed: int = 0) -> np.ndarray:
    """Mã hoá tập train out-of-fold: dòng ở fold k được mã hoá bằng bảng học từ các fold còn lại.

    Chia fold bằng KFold(n_splits, shuffle=True, random_state=seed); prior cũng học từ các fold còn lại.
    """
    # TODO: với mỗi (fit_idx, enc_idx) của KFold: fit trên fit_idx, transform enc_idx
    raise NotImplementedError
