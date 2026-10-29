"""Profiling một bảng: thiếu, trùng khoá, giá trị ngoại lai."""

from __future__ import annotations

import numpy as np
import pandas as pd

PROFILE_COLUMNS = ["dtype", "n_missing", "missing_rate", "n_unique", "top_value", "top_share"]


def profile(df: pd.DataFrame) -> pd.DataFrame:
    """Mỗi cột của df là một dòng (giữ thứ tự cột), các cột kết quả theo PROFILE_COLUMNS.

    dtype        str(kiểu dữ liệu)
    n_missing    số ô NaN/None
    missing_rate n_missing / số dòng (0.0 nếu bảng rỗng)
    n_unique     số giá trị khác nhau, không tính NaN
    top_value    giá trị xuất hiện nhiều nhất (không tính NaN); None nếu cột toàn NaN
    top_share    số lần xuất hiện của top_value / số ô không thiếu; NaN nếu cột toàn NaN
    """
    # TODO: duyệt từng cột, dùng isna(), nunique(), value_counts()
    raise NotImplementedError


def duplicate_report(df: pd.DataFrame, key: list[str]) -> dict[str, int]:
    """Kiểm tra key có thật sự là khoá.

    n_rows              số dòng
    n_unique_keys       số giá trị key khác nhau
    n_rows_dup_key      số dòng có key xuất hiện hơn một lần (đếm mọi bản, không chỉ bản thừa)
    n_exact_duplicates  số dòng trùng hoàn toàn với một dòng đứng trước (df.duplicated())
    """
    # TODO
    raise NotImplementedError


def iqr_outliers(s: pd.Series, k: float = 1.5) -> pd.Series:
    """Mask bool (cùng index với s): giá trị ngoài [Q1 − k·IQR, Q3 + k·IQR]. NaN → False.

    Q1, Q3 là quantile 0.25, 0.75 theo mặc định của pandas (nội suy tuyến tính), bỏ qua NaN.
    """
    # TODO
    raise NotImplementedError
