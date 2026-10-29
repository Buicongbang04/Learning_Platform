"""Đo tác động của hệ thống cảnh báo bằng holdout, và tránh feedback loop khi retrain.

Log quyết định có các cột:
  flagged  bool  đơn vượt ngưỡng cảnh báo
  holdout  bool  đơn được cảnh báo nhưng bị giữ lại ngẫu nhiên, không can thiệp (chỉ True khi flagged)
  treated  bool  đơn thật sự được can thiệp = flagged & ~holdout
  bad      0/1   kết quả (review xấu)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

def naive_effect(log: pd.DataFrame) -> float:
    """Tỉ lệ bad ở đơn được can thiệp trừ tỉ lệ bad ở mọi đơn không được can thiệp."""
    # TODO
    raise NotImplementedError

def holdout_effect(log: pd.DataFrame, alpha: float = 0.05) -> tuple[float, float, float]:
    """(diff, lo, hi): trong các đơn flagged, tỉ lệ bad nhóm treated trừ nhóm holdout, CI normal không pooled."""
    # TODO
    raise NotImplementedError

def realized_value(log: pd.DataFrame, cost_action: float, loss_event: float,
                   alpha: float = 0.05) -> tuple[float, float, float]:
    """(value, lo, hi): giá trị mỗi đơn được can thiệp = −diff * loss_event − cost_action, CI suy từ CI của diff."""
    # TODO
    raise NotImplementedError

def retraining_rows(log: pd.DataFrame, holdout_share: float) -> pd.DataFrame:
    """Các dòng dùng để retrain model rủi ro: bỏ đơn được can thiệp, thêm cột weight.

    weight = 1 cho đơn không flagged, 1 / holdout_share cho đơn holdout (đại diện cho cả nhóm flagged).
    """
    # TODO
    raise NotImplementedError

