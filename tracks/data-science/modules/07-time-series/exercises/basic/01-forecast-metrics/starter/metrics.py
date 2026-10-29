"""Metric cho bài toán dự báo: MAE, RMSE, MAPE, sMAPE, MASE.

Mọi hàm nhận array-like (list, numpy, pandas Series) và trả về float.
MAPE và sMAPE trả về **tỉ lệ** (0.12 nghĩa là 12%), giống sklearn.
"""

from __future__ import annotations

import numpy as np


def mae(y_true, y_pred) -> float:
    """Mean Absolute Error."""
    # TODO
    raise NotImplementedError


def rmse(y_true, y_pred) -> float:
    """Root Mean Squared Error."""
    # TODO
    raise NotImplementedError


def mape(y_true, y_pred) -> float:
    """Mean Absolute Percentage Error, dạng tỉ lệ. ValueError nếu y_true có giá trị 0."""
    # TODO: mean(|y - ŷ| / |y|)
    raise NotImplementedError


def smape(y_true, y_pred) -> float:
    """Symmetric MAPE: mean(2|y - ŷ| / (|y| + |ŷ|)), trong khoảng [0, 2]. Cặp 0/0 tính là 0."""
    # TODO
    raise NotImplementedError


def mase(y_true, y_pred, y_train, m: int = 1) -> float:
    """Mean Absolute Scaled Error.

    Chia MAE của dự báo cho MAE in-sample của seasonal naive bậc m trên y_train:
    mean(|y_train[t] - y_train[t - m]|). ValueError nếu mẫu số bằng 0.
    """
    # TODO
    raise NotImplementedError
