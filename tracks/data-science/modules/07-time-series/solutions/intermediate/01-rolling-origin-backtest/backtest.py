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
    if window is not None and window > initial:
        raise ValueError("window dài hơn số điểm train ở origin đầu tiên")
    splits = []
    for cutoff in range(initial, n - horizon + 1, step):
        start = 0 if window is None else cutoff - window
        splits.append((np.arange(start, cutoff), np.arange(cutoff, cutoff + horizon)))
    if not splits:
        raise ValueError("Không có origin nào đủ horizon điểm test")
    return splits


def backtest(y, forecast_fn: Forecaster, initial: int, horizon: int, step: int = 1,
             window: int | None = None) -> pd.DataFrame:
    """Chạy forecast_fn ở mỗi origin. Cột: cutoff (vị trí điểm test đầu), h (1..horizon), y_true, y_pred.

    forecast_fn chỉ được thấy một **bản sao** dữ liệu train của origin đó.
    """
    values = np.asarray(y, dtype=float)
    rows = []
    for train_idx, test_idx in rolling_origin_splits(len(values), initial, horizon, step, window):
        pred = np.asarray(forecast_fn(values[train_idx].copy(), horizon), dtype=float)
        if pred.shape != (horizon,):
            raise ValueError(f"forecast_fn trả về {pred.shape}, cần ({horizon},)")
        rows.append(pd.DataFrame({
            "cutoff": test_idx[0],
            "h": np.arange(1, horizon + 1),
            "y_true": values[test_idx],
            "y_pred": pred,
        }))
    return pd.concat(rows, ignore_index=True)


def error_by_horizon(results: pd.DataFrame) -> pd.Series:
    """MAE theo từng bước h (index 1..horizon)."""
    return (results.y_true - results.y_pred).abs().groupby(results.h).mean()


def compare(y, forecasters: dict[str, Forecaster], initial: int, horizon: int, step: int = 1,
            window: int | None = None, m: int = 1) -> pd.DataFrame:
    """Bảng index = tên model, cột ['mae', 'mase'], sắp tăng dần theo mase.

    mae: MAE trên mọi điểm test. mase: trung bình qua các origin của
    MAE(origin) / mean(|train[t] - train[t-m]|), mẫu số tính trên train **của origin đó**.
    """
    values = np.asarray(y, dtype=float)
    scales = {}
    for train_idx, test_idx in rolling_origin_splits(len(values), initial, horizon, step, window):
        train = values[train_idx]
        scales[test_idx[0]] = np.mean(np.abs(train[m:] - train[:-m]))
    table = {}
    for name, fn in forecasters.items():
        res = backtest(values, fn, initial, horizon, step, window)
        abs_err = (res.y_true - res.y_pred).abs()
        per_origin = abs_err.groupby(res.cutoff).mean()
        table[name] = {
            "mae": abs_err.mean(),
            "mase": (per_origin / per_origin.index.map(scales)).mean(),
        }
    return pd.DataFrame.from_dict(table, orient="index")[["mae", "mase"]].sort_values("mase")
