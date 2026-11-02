"""Độ tương đồng giữa vector, kNN chính xác và recall của ANN, viết bằng numpy.

Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import numpy as np

METRICS = ("dot", "cosine", "l2")


def l2_normalize(x: np.ndarray) -> np.ndarray:
    """Chia mỗi vector (mỗi dòng nếu 2 chiều) cho chuẩn L2 của nó; vector 0 giữ nguyên 0. Trả float32, không sửa x."""
    # TODO
    raise NotImplementedError


def pairwise(queries: np.ndarray, base: np.ndarray, metric: str) -> np.ndarray:
    """Ma trận (n_queries, n_base): tích vô hướng, cosine, hoặc bình phương khoảng cách Euclid (luôn >= 0)."""
    # TODO
    raise NotImplementedError


def knn(queries: np.ndarray, base: np.ndarray, k: int, metric: str) -> np.ndarray:
    """Chỉ số min(k, n_base) vector gần nhất cho mỗi query, tốt nhất trước; bằng điểm thì chỉ số nhỏ trước."""
    # TODO
    raise NotImplementedError


def ann_recall(approx: np.ndarray, exact: np.ndarray, k: int) -> float:
    """Trung bình theo query của |top-k xấp xỉ ∩ top-k chính xác| / k."""
    # TODO
    raise NotImplementedError
