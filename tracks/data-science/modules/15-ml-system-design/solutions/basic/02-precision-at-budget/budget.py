"""Precision@k, recall@k và đánh giá theo ngân sách hành động mỗi tuần."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd


def k_from_budget(budget: float, cost_per_action: float, n_candidates: int) -> int:
    """Số hành động làm được với ngân sách: floor(budget / cost), không vượt n_candidates."""
    return int(min(math.floor(budget / cost_per_action), n_candidates))


def _top_hits(y_true, scores, k):
    if k < 1:
        raise ValueError("k phải >= 1")
    y = np.asarray(y_true)
    k = min(int(k), len(y))
    top = np.argsort(-np.asarray(scores, dtype=float), kind="stable")[:k]
    return int(y[top].sum()), k, int(y.sum())


def precision_at_k(y_true: Sequence[int], scores: Sequence[float], k: int) -> float:
    """Tỉ lệ ca dương trong top k theo scores giảm dần. k > n thì lấy hết; k < 1 thì ValueError."""
    hits, k, _ = _top_hits(y_true, scores, k)
    return hits / k


def recall_at_k(y_true: Sequence[int], scores: Sequence[float], k: int) -> float:
    """Tỉ lệ ca dương nằm trong top k. Không có ca dương nào thì nan; k < 1 thì ValueError."""
    hits, _, positives = _top_hits(y_true, scores, k)
    return hits / positives if positives else float("nan")


def weekly_at_k(df: pd.DataFrame, k: int, week_col: str = "week", score_col: str = "score",
                label_col: str = "label") -> pd.DataFrame:
    """Mỗi tuần (index, sắp tăng) một dòng: n, positives, selected = min(k, n), hits, precision, recall."""
    rows = []
    for week, g in df.groupby(week_col, sort=True):
        hits, selected, positives = _top_hits(g[label_col], g[score_col], min(k, len(g)))
        rows.append({week_col: week, "n": len(g), "positives": positives, "selected": selected, "hits": hits,
                     "precision": hits / selected,
                     "recall": hits / positives if positives else float("nan")})
    return pd.DataFrame(rows).set_index(week_col)
