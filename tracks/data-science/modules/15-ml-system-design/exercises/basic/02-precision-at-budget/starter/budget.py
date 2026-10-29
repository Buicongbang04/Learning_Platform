"""Precision@k, recall@k và đánh giá theo ngân sách hành động mỗi tuần."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


def k_from_budget(budget: float, cost_per_action: float, n_candidates: int) -> int:
    """Số hành động làm được với ngân sách: floor(budget / cost), không vượt n_candidates."""
    # TODO
    raise NotImplementedError


def precision_at_k(y_true: Sequence[int], scores: Sequence[float], k: int) -> float:
    """Tỉ lệ ca dương trong top k theo scores giảm dần. k > n thì lấy hết; k < 1 thì ValueError."""
    # TODO
    raise NotImplementedError


def recall_at_k(y_true: Sequence[int], scores: Sequence[float], k: int) -> float:
    """Tỉ lệ ca dương nằm trong top k. Không có ca dương nào thì nan; k < 1 thì ValueError."""
    # TODO
    raise NotImplementedError


def weekly_at_k(df: pd.DataFrame, k: int, week_col: str = "week", score_col: str = "score",
                label_col: str = "label") -> pd.DataFrame:
    """Mỗi tuần (index, sắp tăng) một dòng: n, positives, selected = min(k, n), hits, precision, recall."""
    # TODO
    raise NotImplementedError
