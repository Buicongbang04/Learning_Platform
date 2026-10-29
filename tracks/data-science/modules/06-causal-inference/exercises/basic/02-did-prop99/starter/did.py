"""Difference-in-Differences: ước lượng 2x2, hồi quy two-way fixed effects và kiểm tra pre-trend.

Quy ước cột: `treated` = 1 cho đơn vị nhận can thiệp (cả trước lẫn sau), `post` = 1 cho giai đoạn
sau can thiệp (cho mọi đơn vị). Can thiệp xảy ra cùng một thời điểm cho mọi đơn vị treated.
"""

from __future__ import annotations

import pandas as pd
import statsmodels.formula.api as smf


def did_2x2(df: pd.DataFrame, outcome: str, treated: str, post: str) -> float:
    """(mean treated sau − mean treated trước) − (mean control sau − mean control trước)."""
    # TODO: groupby([treated, post]) rồi lấy bốn trung bình
    raise NotImplementedError


def did_regression(df: pd.DataFrame, outcome: str, unit: str, time: str, treated: str,
                   post: str) -> tuple[float, float]:
    """Two-way fixed effects: outcome ~ C(unit) + C(time) + treated:post.

    Trả (hệ số của treated:post, standard error cluster theo unit). Dùng statsmodels formula với
    cov_type="cluster", groups là mã số nguyên của unit (pd.factorize).
    """
    # TODO
    raise NotImplementedError


def pretrend_slope_gap(df: pd.DataFrame, outcome: str, time: str, treated: str, post: str) -> float:
    """Chỉ trên giai đoạn trước can thiệp (post == 0): hồi quy outcome ~ time * treated,
    trả hệ số tương tác time:treated (nhóm treated dốc hơn control bao nhiêu mỗi đơn vị thời gian).
    """
    # TODO: lọc post == 0; chú ý tên cột trong công thức là biến, dùng f-string
    raise NotImplementedError
