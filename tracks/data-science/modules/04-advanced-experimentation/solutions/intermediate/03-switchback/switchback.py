"""Switchback experiment cho marketplace có nguồn cung giới hạn (tài xế, shipper).

Đơn vị random là KHOẢNG THỜI GIAN (period), không phải user: trong một period mọi user cùng nhánh.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def switchback_schedule(n_periods: int, block: int, seed: int = 0) -> np.ndarray:
    """Mảng int 0/1 dài n_periods. Các period gom thành block liên tiếp `block` period, cả block cùng
    một nhánh. Số block treatment và control lệch nhau tối đa 1, thứ tự block ngẫu nhiên."""
    rng = np.random.default_rng(seed)
    n_blocks = -(-n_periods // block)
    arms = rng.permutation(np.arange(n_blocks) % 2)
    return np.repeat(arms, block)[:n_periods].astype(int)


def _welch(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    return float(b.mean() - a.mean()), float(np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)))


def switchback_estimate(periods: pd.DataFrame, burn_in: int = 0) -> dict:
    """periods: cột period, treat (0/1), users, orders. Metric mỗi period = orders / users.

    Bỏ `burn_in` period đầu của mỗi đoạn liên tiếp cùng nhánh (kể cả đoạn đầu tiên của chuỗi),
    vì đó là lúc hệ thống còn mang trạng thái của nhánh trước (carryover).
    Trả dict diff (treatment − control), se (Welch trên các period còn lại), n_used.
    """
    p = periods.sort_values("period").reset_index(drop=True)
    run_id = (p.treat != p.treat.shift()).cumsum()
    position = p.groupby(run_id).cumcount()
    kept = p[position >= burn_in]
    rate = kept.orders / kept.users
    diff, se = _welch(rate[kept.treat == 0].to_numpy(), rate[kept.treat == 1].to_numpy())
    return {"diff": diff, "se": se, "n_used": int(len(kept))}


def user_split_estimate(users: pd.DataFrame) -> dict:
    """users: mỗi dòng một user-period, cột treat (0/1), orders. Hiệu trung bình kèm SE Welch."""
    diff, se = _welch(users.loc[users.treat == 0, "orders"].to_numpy(dtype=float),
                      users.loc[users.treat == 1, "orders"].to_numpy(dtype=float))
    return {"diff": diff, "se": se}
