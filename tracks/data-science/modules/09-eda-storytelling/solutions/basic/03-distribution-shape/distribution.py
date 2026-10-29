"""Tóm tắt hình dạng phân phối và quyết định cách vẽ."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def shape_summary(s: pd.Series) -> dict[str, float]:
    """Tóm tắt một biến số. Mọi thống kê tính trên phần không thiếu.

    n, n_missing, mean, median, std (pandas, ddof=1), skew (pandas Series.skew),
    p01, p99 (quantile 0.01 / 0.99, nội suy mặc định của pandas),
    zero_share (tỉ lệ giá trị bằng 0 trên phần không thiếu),
    tail_ratio = p99 / median (NaN nếu median <= 0).
    """
    x = s.dropna()
    median = float(x.median())
    p01, p99 = (float(v) for v in x.quantile([0.01, 0.99]))
    return {
        "n": int(len(x)),
        "n_missing": int(s.isna().sum()),
        "mean": float(x.mean()),
        "median": median,
        "std": float(x.std()),
        "skew": float(x.skew()),
        "p01": p01,
        "p99": p99,
        "zero_share": float((x == 0).mean()),
        "tail_ratio": p99 / median if median > 0 else math.nan,
    }


def suggest_scale(s: pd.Series, tail_threshold: float = 10.0) -> str:
    """"linear", "log" hoặc "log1p" cho trục giá trị, xét trên phần không thiếu, theo thứ tự:

    1. có giá trị âm → "linear"
    2. tail_ratio không xác định hoặc < tail_threshold → "linear"
    3. có giá trị bằng 0 → "log1p"
    4. còn lại → "log"
    """
    x = s.dropna()
    if (x < 0).any():
        return "linear"
    ratio = shape_summary(x)["tail_ratio"]
    if math.isnan(ratio) or ratio < tail_threshold:
        return "linear"
    if (x == 0).any():
        return "log1p"
    return "log"


def fd_bins(s: pd.Series) -> int:
    """Số bins theo Freedman–Diaconis: h = 2·IQR·n^(−1/3), bins = ceil((max − min) / h).

    Bỏ NaN. IQR = 0 (hoặc max = min) thì dùng Sturges: ceil(log2(n)) + 1. Luôn trả ít nhất 1.
    """
    x = s.dropna().to_numpy(dtype=float)
    n = len(x)
    q1, q3 = np.percentile(x, [25, 75])
    iqr = q3 - q1
    span = x.max() - x.min()
    if iqr == 0 or span == 0:
        return max(1, math.ceil(math.log2(n)) + 1)
    h = 2 * iqr * n ** (-1 / 3)
    return max(1, math.ceil(span / h))


def ecdf(s: pd.Series) -> pd.DataFrame:
    """ECDF: DataFrame cột x (giá trị đã sắp tăng dần, bỏ NaN) và y = i / n với i = 1..n."""
    x = np.sort(s.dropna().to_numpy())
    n = len(x)
    return pd.DataFrame({"x": x, "y": np.arange(1, n + 1) / n})
