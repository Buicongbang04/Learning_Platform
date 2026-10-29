"""Difference-in-Differences: ước lượng 2x2, hồi quy two-way fixed effects và kiểm tra pre-trend.

Quy ước cột: `treated` = 1 cho đơn vị nhận can thiệp (cả trước lẫn sau), `post` = 1 cho giai đoạn
sau can thiệp (cho mọi đơn vị). Can thiệp xảy ra cùng một thời điểm cho mọi đơn vị treated.
"""

from __future__ import annotations

import pandas as pd
import statsmodels.formula.api as smf


def did_2x2(df: pd.DataFrame, outcome: str, treated: str, post: str) -> float:
    """(mean treated sau − mean treated trước) − (mean control sau − mean control trước)."""
    m = df.groupby([treated, post])[outcome].mean()
    return float((m[1, 1] - m[1, 0]) - (m[0, 1] - m[0, 0]))


def did_regression(df: pd.DataFrame, outcome: str, unit: str, time: str, treated: str,
                   post: str) -> tuple[float, float]:
    """Two-way fixed effects: outcome ~ C(unit) + C(time) + treated:post, SE cluster theo unit."""
    fit = smf.ols(f"{outcome} ~ C({unit}) + C({time}) + {treated}:{post}", df).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(df[unit])[0]})
    term = f"{treated}:{post}"
    return float(fit.params[term]), float(fit.bse[term])


def pretrend_slope_gap(df: pd.DataFrame, outcome: str, time: str, treated: str, post: str) -> float:
    """Hệ số time:treated của outcome ~ time * treated trên giai đoạn trước can thiệp."""
    pre = df[df[post] == 0]
    fit = smf.ols(f"{outcome} ~ {time} * {treated}", pre).fit()
    return float(fit.params[f"{time}:{treated}"])
