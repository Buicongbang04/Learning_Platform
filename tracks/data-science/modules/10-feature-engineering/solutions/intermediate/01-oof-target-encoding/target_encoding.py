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
    y = pd.Series(np.asarray(y, dtype=float), index=categories.index)
    prior = float(y.mean())
    stats = y.groupby(categories.to_numpy()).agg(["sum", "count"])
    mapping = (stats["sum"] + smoothing * prior) / (stats["count"] + smoothing)
    return mapping, prior


def transform_target_encoding(categories: pd.Series, mapping: pd.Series, prior: float) -> np.ndarray:
    """Tra bảng; category chưa gặp hoặc NaN nhận prior."""
    return pd.Series(categories).map(mapping).fillna(prior).to_numpy(dtype=float)


def oof_target_encoding(categories: pd.Series, y, n_splits: int = 5, smoothing: float = 20.0,
                        seed: int = 0) -> np.ndarray:
    """Mã hoá tập train out-of-fold: dòng ở fold k được mã hoá bằng bảng học từ các fold còn lại.

    Chia fold bằng KFold(n_splits, shuffle=True, random_state=seed); prior cũng học từ các fold còn lại.
    """
    categories = pd.Series(categories).reset_index(drop=True)
    y = np.asarray(y, dtype=float)
    out = np.empty(len(categories))
    for fit_idx, enc_idx in KFold(n_splits, shuffle=True, random_state=seed).split(categories):
        mapping, prior = fit_target_encoding(categories.iloc[fit_idx], y[fit_idx], smoothing)
        out[enc_idx] = transform_target_encoding(categories.iloc[enc_idx], mapping, prior)
    return out
