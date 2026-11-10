"""Thước đo retrieval: recall@k, MRR@k, nDCG@k (gain nhị phân), trung bình trên các truy vấn.

`retrieved[i]` là danh sách id hệ thống trả về cho truy vấn i (thứ tự giảm dần độ liên quan, không trùng),
`relevant[i]` là tập id đúng của truy vấn đó. Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

import math


def _check(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> None:
    if k < 1:
        raise ValueError(f"k phải >= 1, nhận {k}")
    if len(retrieved) != len(relevant):
        raise ValueError(f"{len(retrieved)} danh sách kết quả nhưng {len(relevant)} tập đáp án")
    if not retrieved:
        raise ValueError("không có truy vấn nào")
    for i, rel in enumerate(relevant):
        if not rel:
            raise ValueError(f"truy vấn {i} không có tài liệu liên quan: recall và nDCG không xác định")


def recall_at_k(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float:
    """Trung bình |Rel ∩ top-k| / |Rel|."""
    _check(retrieved, relevant, k)
    return sum(len(rel & set(ret[:k])) / len(rel) for ret, rel in zip(retrieved, relevant)) / len(relevant)


def mrr_at_k(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float:
    """Trung bình 1 / hạng của tài liệu đúng đầu tiên trong top-k (không có thì 0)."""
    _check(retrieved, relevant, k)
    total = 0.0
    for ret, rel in zip(retrieved, relevant):
        total += next((1 / rank for rank, doc in enumerate(ret[:k], start=1) if doc in rel), 0.0)
    return total / len(relevant)


def ndcg_at_k(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float:
    """Trung bình DCG@k / IDCG@k, gain nhị phân; IDCG là DCG khi mọi tài liệu đúng đứng đầu."""
    _check(retrieved, relevant, k)
    total = 0.0
    for ret, rel in zip(retrieved, relevant):
        dcg = sum(1 / math.log2(rank + 1) for rank, doc in enumerate(ret[:k], start=1) if doc in rel)
        idcg = sum(1 / math.log2(rank + 1) for rank in range(1, min(len(rel), k) + 1))
        total += dcg / idcg
    return total / len(relevant)
