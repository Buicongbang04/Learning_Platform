"""Metric xếp hạng @k cho recommender system (relevance nhị phân)."""

from __future__ import annotations

from typing import Callable, Hashable, Iterable, Mapping, Sequence

import numpy as np


def precision_at_k(recommended: Sequence[Hashable], relevant: Iterable[Hashable], k: int) -> float:
    """Số item relevant trong k gợi ý đầu, chia cho k (kể cả khi danh sách ngắn hơn k)."""
    relevant = set(relevant)
    return sum(item in relevant for item in recommended[:k]) / k


def recall_at_k(recommended: Sequence[Hashable], relevant: Iterable[Hashable], k: int) -> float:
    """Số item relevant trong k gợi ý đầu, chia cho tổng số item relevant; 0 nếu không có relevant."""
    relevant = set(relevant)
    if not relevant:
        return 0.0
    return sum(item in relevant for item in recommended[:k]) / len(relevant)


def average_precision_at_k(recommended: Sequence[Hashable], relevant: Iterable[Hashable], k: int) -> float:
    """AP@k = (1 / min(|relevant|, k)) · Σ precision@i tại mỗi vị trí i ≤ k có item relevant."""
    relevant = set(relevant)
    if not relevant:
        return 0.0
    hits, total = 0, 0.0
    for i, item in enumerate(recommended[:k], start=1):
        if item in relevant:
            hits += 1
            total += hits / i
    return total / min(len(relevant), k)


def ndcg_at_k(recommended: Sequence[Hashable], relevant: Iterable[Hashable], k: int) -> float:
    """DCG@k / IDCG@k với gain nhị phân, DCG = Σ rel_i / log2(i + 1)."""
    relevant = set(relevant)
    if not relevant:
        return 0.0
    dcg = sum(1 / np.log2(i + 1) for i, item in enumerate(recommended[:k], start=1) if item in relevant)
    idcg = sum(1 / np.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return float(dcg / idcg)


def mean_at_k(recs: Mapping[Hashable, Sequence[Hashable]], truth: Mapping[Hashable, Iterable[Hashable]],
              metric: Callable[[Sequence[Hashable], Iterable[Hashable], int], float], k: int) -> float:
    """Trung bình metric trên mọi user có trong truth; user không có gợi ý tính như danh sách rỗng."""
    users = list(truth)
    if not users:
        return 0.0
    return float(np.mean([metric(list(recs.get(u, [])), truth[u], k) for u in users]))
