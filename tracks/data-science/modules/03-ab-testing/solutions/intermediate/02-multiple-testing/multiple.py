"""Lời giải: hiệu chỉnh multiple testing."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def bonferroni(pvals: Sequence[float], alpha: float = 0.05) -> list[bool]:
    m = len(pvals)
    return [bool(p <= alpha / m) for p in pvals]


def holm(pvals: Sequence[float], alpha: float = 0.05) -> list[bool]:
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    reject = np.zeros(m, dtype=bool)
    for rank, idx in enumerate(np.argsort(p, kind="stable")):
        if p[idx] > alpha / (m - rank):
            break
        reject[idx] = True
    return reject.tolist()


def benjamini_hochberg(pvals: Sequence[float], alpha: float = 0.05) -> list[bool]:
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p, kind="stable")
    passed = np.nonzero(p[order] <= alpha * np.arange(1, m + 1) / m)[0]
    reject = np.zeros(m, dtype=bool)
    if passed.size:
        reject[order[: passed.max() + 1]] = True
    return reject.tolist()
