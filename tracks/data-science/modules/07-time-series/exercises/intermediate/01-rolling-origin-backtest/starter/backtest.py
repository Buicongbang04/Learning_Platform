"""Backtesting kiểu rolling origin (time series cross-validation), tự viết.

forecast_fn có chữ ký forecast_fn(train: np.ndarray, horizon: int) -> array độ dài horizon.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

Forecaster = Callable[[np.ndarray, int], np.ndarray]


def rolling_origin_splits(n: int, initial: int, horizon: int, step: int = 1,
                          window: int | None = None) -> list[tuple[np.ndarray, np.ndarray]]:
    """Danh sách (train_idx, test_idx) theo vị trí.

    Origin đầu tiên ở `initial` (train = 0..initial-1), sau đó dời `step` mỗi lần, chỉ giữ split có
    đủ `horizon` điểm test. window=None: expanding window; window=k: chỉ k điểm train gần nhất.
    ValueError nếu không có split nào, hoặc window > initial.
    """
    # TODO
    raise NotImplementedError


def backtest(y, forecast_fn: Forecaster, initial: int, horizon: int, step: int = 1,
             window: int | None = None) -> pd.DataFrame:
    """Chạy forecast_fn ở mỗi origin. Cột: cutoff (vị trí điểm test đầu), h (1..horizon), y_true, y_pred.

    forecast_fn chỉ được thấy một **bản sao** dữ liệu train của origin đó.
    """
    # TODO
    raise NotImplementedError


def error_by_horizon(results: pd.DataFrame) -> pd.Series:
    """MAE theo từng bước h (index 1..horizon)."""
    # TODO
    raise NotImplementedError


def compare(y, forecasters: dict[str, Forecaster], initial: int, horizon: int, step: int = 1,
            window: int | None = None, m: int = 1) -> pd.DataFrame:
    """Bảng index = tên model, cột ['mae', 'mase'], sắp tăng dần theo mase.

    mae: MAE trên mọi điểm test. mase: trung bình qua các origin của
    MAE(origin) / mean(|train[t] - train[t-m]|), mẫu số tính trên train **của origin đó**.
    """
    # TODO
    raise NotImplementedError
