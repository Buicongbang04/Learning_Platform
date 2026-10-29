"""Bốn baseline mà mọi dự báo phải thắng trước khi được dùng.

Mọi hàm nhận y (array-like, quan sát theo thứ tự thời gian) và h (số bước cần dự báo),
trả về np.ndarray độ dài h.
"""

from __future__ import annotations

import numpy as np


def naive(y, h: int) -> np.ndarray:
    """Lặp lại giá trị cuối cùng."""
    # TODO
    raise NotImplementedError


def mean_forecast(y, h: int, window: int | None = None) -> np.ndarray:
    """Trung bình của toàn bộ lịch sử, hoặc của `window` quan sát cuối nếu có."""
    # TODO
    raise NotImplementedError


def drift(y, h: int) -> np.ndarray:
    """Kéo dài đường thẳng nối quan sát đầu và cuối: y_T + k * (y_T - y_1) / (T - 1)."""
    # TODO
    raise NotImplementedError


def seasonal_naive(y, h: int, m: int) -> np.ndarray:
    """Lặp lại mùa vụ cuối: ŷ[T + k] = y[T + k - m * ceil(k / m)]. ValueError nếu len(y) < m."""
    # TODO
    raise NotImplementedError
