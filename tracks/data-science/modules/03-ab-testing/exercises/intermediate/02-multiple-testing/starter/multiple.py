"""Hiệu chỉnh multiple testing: Bonferroni, Holm, Benjamini-Hochberg.

Mỗi hàm nhận danh sách p-value (thứ tự bất kỳ) và trả danh sách bool cùng thứ tự: True là bác bỏ H0.
Không dùng statsmodels.stats.multitest (test dùng nó để đối chiếu).
"""

from __future__ import annotations

from typing import Sequence


def bonferroni(pvals: Sequence[float], alpha: float = 0.05) -> list[bool]:
    """Bác bỏ khi p <= alpha / m."""
    # TODO
    raise NotImplementedError


def holm(pvals: Sequence[float], alpha: float = 0.05) -> list[bool]:
    """Step-down: sắp tăng dần, bác bỏ khi p_(k) <= alpha / (m − k + 1), dừng ở lần đầu không bác bỏ được."""
    # TODO
    raise NotImplementedError


def benjamini_hochberg(pvals: Sequence[float], alpha: float = 0.05) -> list[bool]:
    """Step-up: tìm k lớn nhất có p_(k) <= k · alpha / m, bác bỏ k p-value nhỏ nhất."""
    # TODO
    raise NotImplementedError
