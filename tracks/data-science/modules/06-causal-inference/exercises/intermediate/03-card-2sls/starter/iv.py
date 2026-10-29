"""Instrumental variables: Wald estimator, first stage và 2SLS tự viết bằng numpy.

Mọi hàm nhận DataFrame và tên cột. Một biến nội sinh (endog), một instrument, danh sách biến ngoại
sinh (exog, có thể rỗng). Luôn thêm hằng số vào hồi quy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def wald_estimator(df: pd.DataFrame, outcome: str, endog: str, instrument: str) -> float:
    """Instrument nhị phân, không biến kiểm soát:
    (E[y | z=1] − E[y | z=0]) / (E[d | z=1] − E[d | z=0])."""
    # TODO
    raise NotImplementedError


def first_stage(df: pd.DataFrame, endog: str, instrument: str, exog: list[str]) -> tuple[float, float]:
    """Hồi quy OLS endog ~ 1 + instrument + exog.

    Trả (hệ số của instrument, F-statistic của instrument). Với một instrument, F = t², trong đó
    t dùng SE thông thường (homoskedastic, phương sai phần dư chia cho n − k).
    """
    # TODO
    raise NotImplementedError


def two_sls(df: pd.DataFrame, outcome: str, endog: str, instrument: str, exog: list[str]) -> tuple[float, float]:
    """2SLS: trả (hệ số của endog, standard error thông thường).

    X = [1, endog, exog], Z = [1, instrument, exog].
    Bước 1: X̂ = Z (Z'Z)⁻¹ Z'X.   Bước 2: β = (X̂'X)⁻¹ X̂'y.
    SE: phần dư u = y − Xβ dùng X THẬT (không phải X̂); σ² = u'u / (n − k); Var(β) = σ² (X̂'X̂)⁻¹.
    """
    # TODO
    raise NotImplementedError
