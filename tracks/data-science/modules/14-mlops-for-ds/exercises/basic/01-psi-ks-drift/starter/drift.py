"""Đo data drift: PSI cho biến số và biến phân loại, thống kê KS, mức cảnh báo."""

from __future__ import annotations

import numpy as np
import pandas as pd


def psi(expected, actual, bins: int = 10, eps: float = 1e-4) -> float:
    """Population Stability Index của `actual` so với `expected` (reference).

    - Bỏ NaN ở cả hai mẫu.
    - Biên bin là các quantile 0, 1/bins, ..., 1 của `expected` (np.quantile), bỏ biên trùng
      (np.unique), rồi thay biên đầu bằng -inf và biên cuối bằng +inf để giá trị ngoài khoảng
      của reference vẫn được đếm.
    - Tỉ lệ mỗi bin của hai mẫu được chặn dưới bằng `eps` trước khi lấy log.
    - PSI = sum((a - e) * ln(a / e)).
    """
    # TODO: bỏ NaN, tính biên bin từ expected
    # TODO: tỉ lệ mỗi bin (np.histogram), chặn dưới bằng eps, cộng lại
    raise NotImplementedError


def psi_categorical(expected, actual, eps: float = 1e-4) -> float:
    """PSI cho biến phân loại: mỗi giá trị là một bin, NaN/None là một giá trị riêng.

    Lấy hợp các giá trị của hai mẫu; giá trị vắng mặt ở một mẫu có tỉ lệ 0 (rồi chặn bằng eps).
    """
    # TODO: value_counts(normalize=True, dropna=False) cho từng mẫu, reindex theo hợp các giá trị
    raise NotImplementedError


def ks_statistic(a, b) -> float:
    """Thống kê Kolmogorov-Smirnov hai mẫu: max |F_a(x) - F_b(x)| trên mọi x.

    Tự cài bằng ECDF (không gọi scipy). Bỏ NaN. Phải đúng cả khi dữ liệu có nhiều giá trị trùng.
    """
    # TODO: sắp xếp hai mẫu, tính ECDF của cả hai tại mọi giá trị trong mẫu gộp (np.searchsorted)
    raise NotImplementedError


def drift_level(psi_value: float) -> str:
    """'stable' nếu < 0.1, 'moderate' nếu 0.1 <= psi < 0.25, 'major' nếu >= 0.25."""
    # TODO
    raise NotImplementedError
