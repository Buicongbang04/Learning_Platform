"""Variance Inflation Factor và loại biến lặp theo VIF."""

from __future__ import annotations

import numpy as np
import pandas as pd


def vif(df: pd.DataFrame) -> pd.Series:
    """VIF của từng cột (df không có hằng số; mỗi hồi quy phụ tự thêm hằng số).

    R²_j = 1 (1 - R² < 1e-10) thì VIF = inf. Cột hằng số thì ValueError.
    """
    X = df.to_numpy(dtype=float)
    n, k = X.shape
    constant = [c for c, s in zip(df.columns, X.std(axis=0)) if s == 0]
    if constant:
        raise ValueError(f"Cột hằng số (variance 0), bỏ trước khi tính VIF: {constant}")
    values = []
    for j in range(k):
        y = X[:, j]
        Z = np.column_stack([np.ones(n), np.delete(X, j, axis=1)])
        coef, *_ = np.linalg.lstsq(Z, y, rcond=None)
        e = y - Z @ coef
        one_minus_r2 = (e @ e) / ((y - y.mean()) ** 2).sum()
        values.append(np.inf if one_minus_r2 < 1e-10 else 1 / one_minus_r2)
    return pd.Series(values, index=df.columns, name="vif")


def prune_by_vif(df: pd.DataFrame, threshold: float = 10.0) -> list[str]:
    """Bỏ lặp cột có VIF lớn nhất (> threshold; hoà thì cột đứng trước). Trả cột giữ lại, thứ tự ban đầu."""
    kept = list(df.columns)
    while len(kept) > 1:
        v = vif(df[kept])
        if v.max() <= threshold:
            break
        kept.remove(v.idxmax())          # idxmax trả vị trí đầu tiên khi hoà
    return kept
