"""Chính sách cảnh báo lai (ngưỡng + trần mỗi tuần) và số liệu năng lực cho design doc."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


def weekly_late_volume(orders: pd.DataFrame, start: str = "2017-06-01", end: str = "2018-08-01") -> pd.Series:
    """Số đơn giao xong bị trễ theo tuần mua hàng (tuần kết thúc Chủ nhật, index là ngày Chủ nhật đó).
    Trả về đủ mọi tuần có nhãn trong [start, end), tuần không có đơn trễ nào là 0.

    Đơn giao xong: order_status == "delivered" và có order_delivered_customer_date.
    Trễ: order_delivered_customer_date > order_estimated_delivery_date (so nguyên timestamp).
    """
    # TODO
    raise NotImplementedError


def hybrid_alerts(scores: Sequence[float], weeks: Sequence, threshold: float, cap_per_week: int) -> np.ndarray:
    """Mảng bool: cảnh báo đơn có score >= threshold, nhưng mỗi tuần tối đa cap_per_week đơn có score cao nhất."""
    # TODO
    raise NotImplementedError


def choose_policy(y: Sequence[int], scores: Sequence[float], weeks: Sequence, thresholds: Sequence[float],
                  caps: Sequence[int], cost_action: float, loss_event: float, effect: float) -> dict:
    """Vét cạn (threshold, cap) trên lưới, giá trị = TP * effect * loss_event − số cảnh báo * cost_action.

    Trả dict threshold, cap, value, n_alerts của phương án giá trị lớn nhất; hoà thì chọn phương án ít
    cảnh báo hơn.
    """
    # TODO
    raise NotImplementedError
