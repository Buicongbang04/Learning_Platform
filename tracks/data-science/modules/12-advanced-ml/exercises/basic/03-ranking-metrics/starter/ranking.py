"""Metric xếp hạng @k cho recommender system (relevance nhị phân)."""

from __future__ import annotations

from typing import Callable, Hashable, Iterable, Mapping, Sequence

import numpy as np


def precision_at_k(recommended: Sequence[Hashable], relevant: Iterable[Hashable], k: int) -> float:
    """Số item relevant trong k gợi ý đầu, chia cho k (kể cả khi danh sách ngắn hơn k)."""
    # TODO: đếm item relevant trong recommended[:k]
    raise NotImplementedError


def recall_at_k(recommended: Sequence[Hashable], relevant: Iterable[Hashable], k: int) -> float:
    """Số item relevant trong k gợi ý đầu, chia cho tổng số item relevant; 0 nếu không có relevant."""
    # TODO: nhớ trường hợp không có item relevant
    raise NotImplementedError


def average_precision_at_k(recommended: Sequence[Hashable], relevant: Iterable[Hashable], k: int) -> float:
    """AP@k = (1 / min(|relevant|, k)) · Σ precision@i tại mỗi vị trí i ≤ k có item relevant."""
    # TODO: cộng precision@i tại mỗi vị trí i có hit, chia cho min(|relevant|, k)
    raise NotImplementedError


def ndcg_at_k(recommended: Sequence[Hashable], relevant: Iterable[Hashable], k: int) -> float:
    """DCG@k / IDCG@k với gain nhị phân, DCG = Σ rel_i / log2(i + 1)."""
    # TODO: DCG của danh sách gợi ý, IDCG của danh sách lý tưởng (mọi hit ở đầu, tối đa k)
    raise NotImplementedError


def mean_at_k(recs: Mapping[Hashable, Sequence[Hashable]], truth: Mapping[Hashable, Iterable[Hashable]],
              metric: Callable[[Sequence[Hashable], Iterable[Hashable], int], float], k: int) -> float:
    """Trung bình metric trên mọi user có trong truth; user không có gợi ý tính như danh sách rỗng."""
    # TODO: duyệt user trong truth, recs.get(u, [])
    raise NotImplementedError
