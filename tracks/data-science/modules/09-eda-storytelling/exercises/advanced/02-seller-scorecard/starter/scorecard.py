"""Funnel plot cho seller: ai thật sự giao trễ nhiều hơn mức chung?"""

from __future__ import annotations

import numpy as np
import pandas as pd


def seller_funnel(table: pd.DataFrame, unit: str = "seller_id", target: str = "late",
                  z: float = 3.0) -> pd.DataFrame:
    """Dữ liệu cho funnel plot: một dòng mỗi giá trị của unit (index tên unit).

    Cột (đúng thứ tự): n, events (số dòng target True), rate = events / n,
    expected (tỉ lệ target trên TOÀN BỘ table, giống nhau mọi dòng),
    lower / upper: giới hạn kiểm soát expected ∓ z·sqrt(expected·(1 − expected) / n), cắt vào [0, 1],
    excess = events − expected·n (số sự kiện vượt kỳ vọng),
    flag: "above" nếu rate > upper, "below" nếu rate < lower, ngược lại "within".
    """
    # TODO
    raise NotImplementedError


def alerts(funnel: pd.DataFrame, min_n: int = 20) -> list:
    """Danh sách unit có flag "above" và n >= min_n, sắp theo excess giảm dần."""
    # TODO
    raise NotImplementedError
