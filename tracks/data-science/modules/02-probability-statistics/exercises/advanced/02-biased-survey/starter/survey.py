"""Ước lượng từ mẫu khảo sát bị lệch: post-stratification và inverse probability weighting."""

from __future__ import annotations

import numpy as np
import pandas as pd


def poststratified_mean(sample: pd.DataFrame, y: str, strata: str, pop_shares: pd.Series) -> float:
    """Trung bình của y trên tổng thể, ước lượng bằng post-stratification.

    pop_shares: index là giá trị của cột strata, giá trị là tỉ trọng (hoặc số lượng) trong tổng thể;
    chuẩn hoá về tổng 1. Ước lượng = sum_h W_h * mean(y trong mẫu, tầng h).
    Tầng có tỉ trọng > 0 trong tổng thể mà không có quan sát nào trong mẫu: raise ValueError.
    """
    # TODO
    raise NotImplementedError


def ipw_mean(y: np.ndarray, p_select: np.ndarray) -> float:
    """Trung bình có trọng số 1 / p_select (ước lượng Hajek): sum(y / p) / sum(1 / p)."""
    # TODO
    raise NotImplementedError


def poststrat_bootstrap_ci(sample: pd.DataFrame, y: str, strata: str, pop_shares: pd.Series,
                           n_boot: int = 2000, seed: int = 0,
                           alpha: float = 0.05) -> tuple[float, float, float]:
    """(estimate, lo, hi): estimate = poststratified_mean(...); CI bootstrap percentile.

    Bootstrap **phân tầng**: mỗi lần lặp resample có hoàn lại riêng trong từng tầng (giữ nguyên số
    quan sát mỗi tầng), rồi tính lại ước lượng post-stratified. Dùng np.random.default_rng(seed).
    """
    # TODO
    raise NotImplementedError
