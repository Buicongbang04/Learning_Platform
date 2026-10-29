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
    rows = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        n_missing = int(s.isna().sum())
        counts = s.value_counts(dropna=True)
        rows.append({
            "dtype": str(s.dtype),
            "n_missing": n_missing,
            "missing_rate": n_missing / n if n else 0.0,
            "n_unique": int(s.nunique(dropna=True)),
            "top_value": counts.index[0] if len(counts) else None,
            "top_share": counts.iloc[0] / counts.sum() if len(counts) else np.nan,
        })
    return pd.DataFrame(rows, index=pd.Index(df.columns, name="column"), columns=PROFILE_COLUMNS)


def duplicate_report(df: pd.DataFrame, key: list[str]) -> dict[str, int]:
    """Kiểm tra key có thật sự là khoá.

    n_rows              số dòng
    n_unique_keys       số giá trị key khác nhau
    n_rows_dup_key      số dòng có key xuất hiện hơn một lần (đếm mọi bản, không chỉ bản thừa)
    n_exact_duplicates  số dòng trùng hoàn toàn với một dòng đứng trước (df.duplicated())
    """
    return {
        "n_rows": len(df),
        "n_unique_keys": len(df.drop_duplicates(subset=key)),
        "n_rows_dup_key": int(df.duplicated(subset=key, keep=False).sum()),
        "n_exact_duplicates": int(df.duplicated().sum()),
    }


def iqr_outliers(s: pd.Series, k: float = 1.5) -> pd.Series:
    """Mask bool (cùng index với s): giá trị ngoài [Q1 − k·IQR, Q3 + k·IQR]. NaN → False.

    Q1, Q3 là quantile 0.25, 0.75 theo mặc định của pandas (nội suy tuyến tính), bỏ qua NaN.
    """
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return ((s < q1 - k * iqr) | (s > q3 + k * iqr)).fillna(False).astype(bool)
