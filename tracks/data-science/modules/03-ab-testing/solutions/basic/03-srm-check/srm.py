"""Lời giải: kiểm tra Sample Ratio Mismatch."""

from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.stats import chi2


def srm_pvalue(counts: Sequence[int], expected_ratios: Sequence[float]) -> float:
    observed = np.asarray(counts, dtype=float)
    ratios = np.asarray(expected_ratios, dtype=float)
    expected = observed.sum() * ratios / ratios.sum()
    statistic = ((observed - expected) ** 2 / expected).sum()
    return float(chi2.sf(statistic, df=len(observed) - 1))


def has_srm(counts: Sequence[int], expected_ratios: Sequence[float], threshold: float = 0.001) -> bool:
    return bool(srm_pvalue(counts, expected_ratios) < threshold)
