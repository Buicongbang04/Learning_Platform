"""Đo data drift: PSI cho biến số và biến phân loại, thống kê KS, mức cảnh báo."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clean(x) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return x[~np.isnan(x)]


def psi(expected, actual, bins: int = 10, eps: float = 1e-4) -> float:
    """Population Stability Index của `actual` so với `expected` (reference).

    - Bỏ NaN ở cả hai mẫu.
    - Biên bin là các quantile 0, 1/bins, ..., 1 của `expected` (np.quantile), bỏ biên trùng
      (np.unique), rồi thay biên đầu bằng -inf và biên cuối bằng +inf để giá trị ngoài khoảng
      của reference vẫn được đếm.
    - Tỉ lệ mỗi bin của hai mẫu được chặn dưới bằng `eps` trước khi lấy log.
    - PSI = sum((a - e) * ln(a / e)).
    """
    e_values, a_values = _clean(expected), _clean(actual)
    edges = np.unique(np.quantile(e_values, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:                      # reference là hằng số: một bin duy nhất
        edges = np.array([-np.inf, np.inf])
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.histogram(e_values, edges)[0] / len(e_values)
    a = np.histogram(a_values, edges)[0] / len(a_values)
    e, a = np.clip(e, eps, None), np.clip(a, eps, None)
    return float(np.sum((a - e) * np.log(a / e)))


def psi_categorical(expected, actual, eps: float = 1e-4) -> float:
    """PSI cho biến phân loại: mỗi giá trị là một bin, NaN/None là một giá trị riêng.

    Lấy hợp các giá trị của hai mẫu; giá trị vắng mặt ở một mẫu có tỉ lệ 0 (rồi chặn bằng eps).
    """
    e = pd.Series(expected, dtype=object).fillna("__missing__").value_counts(normalize=True)
    a = pd.Series(actual, dtype=object).fillna("__missing__").value_counts(normalize=True)
    categories = e.index.union(a.index)
    e = e.reindex(categories, fill_value=0.0).clip(lower=eps).to_numpy()
    a = a.reindex(categories, fill_value=0.0).clip(lower=eps).to_numpy()
    return float(np.sum((a - e) * np.log(a / e)))


def ks_statistic(a, b) -> float:
    """Thống kê Kolmogorov-Smirnov hai mẫu: max |F_a(x) - F_b(x)| trên mọi x.

    Tự cài bằng ECDF (không gọi scipy). Bỏ NaN. Phải đúng cả khi dữ liệu có nhiều giá trị trùng.
    """
    a, b = np.sort(_clean(a)), np.sort(_clean(b))
    grid = np.concatenate([a, b])
    # side="right": F(x) = tỉ lệ giá trị <= x, đúng định nghĩa ECDF kể cả khi có giá trị trùng
    cdf_a = np.searchsorted(a, grid, side="right") / len(a)
    cdf_b = np.searchsorted(b, grid, side="right") / len(b)
    return float(np.max(np.abs(cdf_a - cdf_b)))


def drift_level(psi_value: float) -> str:
    """'stable' nếu < 0.1, 'moderate' nếu 0.1 <= psi < 0.25, 'major' nếu >= 0.25."""
    if psi_value < 0.1:
        return "stable"
    if psi_value < 0.25:
        return "moderate"
    return "major"
