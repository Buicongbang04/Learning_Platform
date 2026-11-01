"""Độ tương đồng giữa vector, kNN chính xác và recall của ANN, viết bằng numpy.

Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import numpy as np

METRICS = ("dot", "cosine", "l2")


def l2_normalize(x: np.ndarray) -> np.ndarray:
    """Chia mỗi vector (mỗi dòng nếu 2 chiều) cho chuẩn L2 của nó; vector 0 giữ nguyên 0. Trả float32, không sửa x."""
    x = np.asarray(x, dtype=np.float32)
    norms = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.where(norms == 0, 1, norms)


def pairwise(queries: np.ndarray, base: np.ndarray, metric: str) -> np.ndarray:
    """Ma trận (n_queries, n_base): tích vô hướng, cosine, hoặc bình phương khoảng cách Euclid (luôn >= 0)."""
    q = np.asarray(queries, dtype=np.float32)
    b = np.asarray(base, dtype=np.float32)
    if metric == "dot":
        return q @ b.T
    if metric == "cosine":
        return l2_normalize(q) @ l2_normalize(b).T
    if metric == "l2":
        sq = (q * q).sum(1)[:, None] + (b * b).sum(1)[None, :] - 2 * (q @ b.T)
        return np.maximum(sq, 0)
    raise ValueError(f"metric phải là một trong {METRICS}, nhận {metric!r}")


def knn(queries: np.ndarray, base: np.ndarray, k: int, metric: str) -> np.ndarray:
    """Chỉ số min(k, n_base) vector gần nhất cho mỗi query, tốt nhất trước; bằng điểm thì chỉ số nhỏ trước."""
    scores = pairwise(queries, base, metric)
    key = scores if metric == "l2" else -scores
    return np.argsort(key, axis=1, kind="stable")[:, :k].astype(np.int64)


def ann_recall(approx: np.ndarray, exact: np.ndarray, k: int) -> float:
    """Trung bình theo query của |top-k xấp xỉ ∩ top-k chính xác| / k."""
    hits = [len(set(np.asarray(a)[:k].tolist()) & set(np.asarray(e)[:k].tolist())) for a, e in zip(approx, exact)]
    return float(np.mean(hits) / k)
