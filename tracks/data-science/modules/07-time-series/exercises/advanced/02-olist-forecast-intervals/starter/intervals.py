"""Prediction interval cho dự báo số đơn Olist: dựng từ sai số backtest, chấm bằng coverage và interval score.

forecast_fn có chữ ký forecast_fn(train: np.ndarray, h: int) -> array độ dài h.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def backtest_errors(series: pd.Series, forecast_fn, cutoffs, h: int) -> pd.DataFrame:
    """Mỗi cutoff: train = series trước cutoff, test = h ngày từ cutoff.

    Trả DataFrame cột cutoff, h (1..h), y_true, y_pred; h dòng mỗi cutoff.
    """
    # TODO
    raise NotImplementedError


def empirical_interval(point, backtest: pd.DataFrame, alpha: float = 0.2,
                       kind: str = "additive") -> tuple[np.ndarray, np.ndarray]:
    """Khoảng dự báo 1 - alpha cho dự báo điểm `point` (độ dài H) từ sai số backtest theo từng bước h.

    kind="additive": e = y_true - y_pred; khoảng = point + quantile(e_h, alpha/2), point + quantile(e_h, 1 - alpha/2).
    kind="log_ratio": e = log(y_true / y_pred); khoảng = point * exp(quantile ...).
    Quantile theo np.quantile mặc định (nội suy tuyến tính), tính riêng cho từng h = 1..H.
    ValueError nếu backtest thiếu bước h nào trong 1..H, hoặc kind lạ.
    """
    # TODO
    raise NotImplementedError


def coverage(y, lo, hi) -> float:
    """Tỉ lệ y nằm trong [lo, hi] (tính cả biên)."""
    # TODO
    raise NotImplementedError


def interval_score(y, lo, hi, alpha: float) -> float:
    """Interval score (Gneiting & Raftery 2007), trung bình: độ rộng + phạt 2/alpha × khoảng vượt ra ngoài."""
    # TODO
    raise NotImplementedError


def pinball_loss(y, q_pred, q: float) -> float:
    """Quantile (pinball) loss trung bình của dự báo phân vị q."""
    # TODO
    raise NotImplementedError
