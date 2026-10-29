"""Metric cho bài toán dự báo: MAE, RMSE, MAPE, sMAPE, MASE.

Mọi hàm nhận array-like (list, numpy, pandas Series) và trả về float.
MAPE và sMAPE trả về **tỉ lệ** (0.12 nghĩa là 12%), giống sklearn.
"""

from __future__ import annotations

import numpy as np


def _arrays(y_true, y_pred) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    if y.shape != p.shape:
        raise ValueError(f"Khác kích thước: {y.shape} và {p.shape}")
    return y, p


def mae(y_true, y_pred) -> float:
    """Mean Absolute Error."""
    y, p = _arrays(y_true, y_pred)
    return float(np.mean(np.abs(y - p)))


def rmse(y_true, y_pred) -> float:
    """Root Mean Squared Error."""
    y, p = _arrays(y_true, y_pred)
    return float(np.sqrt(np.mean((y - p) ** 2)))


def mape(y_true, y_pred) -> float:
    """Mean Absolute Percentage Error, dạng tỉ lệ. ValueError nếu y_true có giá trị 0."""
    y, p = _arrays(y_true, y_pred)
    if np.any(y == 0):
        raise ValueError("MAPE không xác định khi giá trị thật bằng 0; dùng MASE hoặc WAPE")
    return float(np.mean(np.abs(y - p) / np.abs(y)))


def smape(y_true, y_pred) -> float:
    """Symmetric MAPE: mean(2|y - ŷ| / (|y| + |ŷ|)), trong khoảng [0, 2]. Cặp 0/0 tính là 0."""
    y, p = _arrays(y_true, y_pred)
    denom = np.abs(y) + np.abs(p)
    ratio = np.divide(2 * np.abs(y - p), denom, out=np.zeros_like(denom), where=denom > 0)
    return float(np.mean(ratio))


def mase(y_true, y_pred, y_train, m: int = 1) -> float:
    """Mean Absolute Scaled Error.

    Chia MAE của dự báo cho MAE in-sample của seasonal naive bậc m trên y_train:
    mean(|y_train[t] - y_train[t - m]|). ValueError nếu mẫu số bằng 0.
    """
    train = np.asarray(y_train, dtype=float)
    if len(train) <= m:
        raise ValueError("y_train phải dài hơn m")
    scale = np.mean(np.abs(train[m:] - train[:-m]))
    if scale == 0:
        raise ValueError("y_train không đổi theo mùa vụ m: mẫu số MASE bằng 0")
    return mae(y_true, y_pred) / float(scale)
