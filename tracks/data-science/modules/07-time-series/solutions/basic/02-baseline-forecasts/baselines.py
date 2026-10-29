"""Bốn baseline mà mọi dự báo phải thắng trước khi được dùng.

Mọi hàm nhận y (array-like, quan sát theo thứ tự thời gian) và h (số bước cần dự báo),
trả về np.ndarray độ dài h.
"""

from __future__ import annotations

import numpy as np


def naive(y, h: int) -> np.ndarray:
    """Lặp lại giá trị cuối cùng."""
    y = np.asarray(y, dtype=float)
    return np.full(h, y[-1])


def mean_forecast(y, h: int, window: int | None = None) -> np.ndarray:
    """Trung bình của toàn bộ lịch sử, hoặc của `window` quan sát cuối nếu có."""
    y = np.asarray(y, dtype=float)
    if window is not None:
        y = y[-window:]
    return np.full(h, y.mean())


def drift(y, h: int) -> np.ndarray:
    """Kéo dài đường thẳng nối quan sát đầu và cuối: y_T + k * (y_T - y_1) / (T - 1)."""
    y = np.asarray(y, dtype=float)
    slope = (y[-1] - y[0]) / (len(y) - 1)
    return y[-1] + slope * np.arange(1, h + 1)


def seasonal_naive(y, h: int, m: int) -> np.ndarray:
    """Lặp lại mùa vụ cuối: ŷ[T + k] = y[T + k - m * ceil(k / m)]. ValueError nếu len(y) < m."""
    y = np.asarray(y, dtype=float)
    if len(y) < m:
        raise ValueError(f"Cần ít nhất một mùa vụ đầy đủ ({m} quan sát), chỉ có {len(y)}")
    last_season = y[-m:]
    return last_season[np.arange(h) % m]
