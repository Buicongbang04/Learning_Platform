"""M01: thước đo retrieval, cùng định nghĩa mục 6 module 13 (bài Basic 03).

`retrieved[i]` là danh sách id trả về cho truy vấn i (giảm dần độ liên quan, không trùng), `relevant[i]` là tập id
đúng. k < 1, hai danh sách khác độ dài, không có truy vấn, hoặc một truy vấn không có id đúng: `ValueError`.
"""

from __future__ import annotations


def recall_at_k(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float:
    """Trung bình |Rel ∩ top-k| / |Rel|."""
    raise NotImplementedError("M01: recall_at_k")


def mrr_at_k(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float:
    """Trung bình 1 / hạng của id đúng đầu tiên trong top-k (không có thì 0)."""
    raise NotImplementedError("M01: mrr_at_k")


def ndcg_at_k(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float:
    """Trung bình DCG@k / IDCG@k, gain nhị phân."""
    raise NotImplementedError("M01: ndcg_at_k")


def first_hit_rank(retrieved: list[str], relevant: set[str]) -> int | None:
    """Hạng (từ 1) của id đúng đầu tiên trong một danh sách; không có thì `None`. Dùng cho phân tích lỗi."""
    raise NotImplementedError("M01: first_hit_rank")
