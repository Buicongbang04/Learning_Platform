"""Thước đo retrieval: recall@k, MRR@k, nDCG@k (gain nhị phân), trung bình trên các truy vấn.

`retrieved[i]` là danh sách id hệ thống trả về cho truy vấn i (thứ tự giảm dần độ liên quan, không trùng),
`relevant[i]` là tập id đúng của truy vấn đó. Mọi hàm trả `float` Python và ném ValueError khi đầu vào
không hợp lệ (xem README). Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

import math


def recall_at_k(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float:
    """Trung bình trên các truy vấn của |Rel ∩ top-k| / |Rel|."""
    # TODO
    raise NotImplementedError


def mrr_at_k(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float:
    """Trung bình trên các truy vấn của 1 / hạng tài liệu đúng đầu tiên trong top-k (không có thì 0)."""
    # TODO
    raise NotImplementedError


def ndcg_at_k(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float:
    """Trung bình trên các truy vấn của DCG@k / IDCG@k, gain nhị phân."""
    # TODO
    raise NotImplementedError
