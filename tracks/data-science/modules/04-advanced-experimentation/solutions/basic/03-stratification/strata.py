"""Stratification: chia tầng khi random (stratified sampling) và khi phân tích (post-stratification).

strata: mảng nhãn tầng (số hoặc chuỗi), mỗi phần tử ứng với một đơn vị random.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def strata_from_quantiles(x: np.ndarray, q: int) -> np.ndarray:
    """Nhãn tầng 0..q−1 theo quantile của x (ví dụ doanh số trước thí nghiệm). Tầng q−1 là x lớn nhất."""
    return pd.qcut(np.asarray(x, dtype=float), q, labels=False).astype(int)


def stratified_assign(strata: np.ndarray, seed: int = 0) -> np.ndarray:
    """Mảng bool (True = treatment). Trong MỖI tầng, số treatment và control lệch nhau tối đa 1.

    Thứ tự trong tầng ngẫu nhiên; tầng có số lẻ đơn vị thì nhánh nhận đơn vị thừa cũng ngẫu nhiên.
    Dùng np.random.default_rng(seed).
    """
    rng = np.random.default_rng(seed)
    strata = np.asarray(strata)
    treat = np.zeros(len(strata), dtype=bool)
    for s in np.unique(strata):
        idx = np.flatnonzero(strata == s)
        order = rng.permutation(idx)
        first_arm = rng.integers(0, 2)          # nhánh nào nhận vị trí chẵn (và đơn vị thừa)
        treat[order] = (np.arange(len(order)) % 2) == first_arm
    return treat


def post_stratified_effect(y: np.ndarray, treat: np.ndarray, strata: np.ndarray, alpha: float = 0.05) -> dict:
    """Ước lượng post-stratified: tổng theo tầng của w_k · (mean_T,k − mean_C,k), w_k = N_k / N.

    SE² = tổng w_k² · (s²_T,k / n_T,k + s²_C,k / n_C,k), ddof=1.
    Trả dict diff, se, ci_low, ci_high. ValueError nếu một tầng có dưới 2 đơn vị ở một nhánh.
    """
    df = pd.DataFrame({"y": np.asarray(y, dtype=float), "t": np.asarray(treat, dtype=bool),
                       "s": np.asarray(strata)})
    cells = df.groupby(["s", "t"]).y.agg(["mean", "var", "size"]).unstack("t")
    if cells["size"].isna().any().any() or (cells["size"] < 2).any().any():
        raise ValueError("Mỗi tầng cần ít nhất 2 đơn vị ở mỗi nhánh")
    w = cells["size"].sum(axis=1) / len(df)
    diff = float((w * (cells["mean"][True] - cells["mean"][False])).sum())
    var = float((w**2 * (cells["var"][True] / cells["size"][True]
                         + cells["var"][False] / cells["size"][False])).sum())
    se = float(np.sqrt(var))
    z = norm.ppf(1 - alpha / 2)
    return {"diff": diff, "se": se, "ci_low": diff - z * se, "ci_high": diff + z * se}
