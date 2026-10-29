"""Switchback experiment cho marketplace có nguồn cung giới hạn (tài xế, shipper).

Đơn vị random là KHOẢNG THỜI GIAN (period), không phải user: trong một period mọi user cùng nhánh.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def switchback_schedule(n_periods: int, block: int, seed: int = 0) -> np.ndarray:
    """Mảng int 0/1 dài n_periods. Các period gom thành block liên tiếp `block` period, cả block cùng
    một nhánh. Số block treatment và control lệch nhau tối đa 1, thứ tự block ngẫu nhiên."""
    # TODO
    raise NotImplementedError


def switchback_estimate(periods: pd.DataFrame, burn_in: int = 0) -> dict:
    """periods: cột period, treat (0/1), users, orders. Metric mỗi period = orders / users.

    Bỏ `burn_in` period đầu của mỗi đoạn liên tiếp cùng nhánh (kể cả đoạn đầu tiên của chuỗi),
    vì đó là lúc hệ thống còn mang trạng thái của nhánh trước (carryover).
    Trả dict diff (treatment − control), se (Welch trên các period còn lại), n_used.
    """
    # TODO
    raise NotImplementedError


def user_split_estimate(users: pd.DataFrame) -> dict:
    """users: mỗi dòng một user-period, cột treat (0/1), orders. Hiệu trung bình kèm SE Welch."""
    # TODO
    raise NotImplementedError
