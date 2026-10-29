"""Kiểm tra Sample Ratio Mismatch (SRM) bằng chi-square goodness-of-fit."""

from __future__ import annotations

from typing import Sequence

from scipy.stats import chi2


def srm_pvalue(counts: Sequence[int], expected_ratios: Sequence[float]) -> float:
    """p-value của kiểm định "số đơn vị mỗi nhánh khớp tỉ lệ thiết kế".

    expected_ratios không cần cộng bằng 1: [1, 1] và [0.5, 0.5] là như nhau.
    """
    # TODO: expected = tổng counts * ratio đã chuẩn hoá
    # TODO: statistic = sum((observed - expected)² / expected), bậc tự do = số nhánh - 1
    raise NotImplementedError


def has_srm(counts: Sequence[int], expected_ratios: Sequence[float], threshold: float = 0.001) -> bool:
    """True nếu p-value nhỏ hơn ngưỡng (ngành thường dùng 0.001)."""
    # TODO
    raise NotImplementedError
