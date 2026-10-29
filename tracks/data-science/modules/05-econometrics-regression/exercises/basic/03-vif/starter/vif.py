"""Variance Inflation Factor và loại biến lặp theo VIF."""

from __future__ import annotations

import numpy as np
import pandas as pd


def vif(df: pd.DataFrame) -> pd.Series:
    """VIF của từng cột (df không có hằng số; mỗi hồi quy phụ tự thêm hằng số).

    R²_j = 1 (1 - R² < 1e-10) thì VIF = inf. Cột hằng số thì ValueError.
    """
    # TODO: kiểm cột hằng số
    # TODO: với mỗi cột j: hồi quy lên [1, các cột khác], R², 1 / (1 - R²)
    raise NotImplementedError


def prune_by_vif(df: pd.DataFrame, threshold: float = 10.0) -> list[str]:
    """Bỏ lặp cột có VIF lớn nhất (> threshold; hoà thì cột đứng trước). Trả cột giữ lại, thứ tự ban đầu."""
    # TODO
    raise NotImplementedError
