"""Metric phân loại tự cài bằng numpy: confusion, precision/recall/F1, ROC-AUC, PR-AUC, log loss.

Không dùng sklearn trong tệp này. Test so kết quả với sklearn.metrics.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.stats import rankdata


def confusion_counts(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, int]:
    """Trả {"tp": ..., "fp": ..., "fn": ..., "tn": ...} (int thường) cho nhãn 0/1."""
    y = np.asarray(y_true).astype(bool)
    pred = np.asarray(y_pred).astype(bool)
    return {
        "tp": int(np.sum(y & pred)),
        "fp": int(np.sum(~y & pred)),
        "fn": int(np.sum(y & ~pred)),
        "tn": int(np.sum(~y & ~pred)),
    }


def precision_recall_f1(y_true: Sequence[int], y_pred: Sequence[int]) -> tuple[float, float, float]:
    """(precision, recall, f1). Mẫu số bằng 0 thì trả 0.0 cho đại lượng đó."""
    c = confusion_counts(y_true, y_pred)
    precision = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
    recall = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return float(precision), float(recall), float(f1)


def roc_auc(y_true: Sequence[int], scores: Sequence[float]) -> float:
    """ROC-AUC = P(score của một ca dương ngẫu nhiên > score của một ca âm ngẫu nhiên),
    tính điểm trùng (tie) là 1/2. Cài bằng thứ hạng (Mann-Whitney), O(n log n), không lặp đôi một.
    """
    y = np.asarray(y_true).astype(bool)
    ranks = rankdata(np.asarray(scores, dtype=float))   # hạng trung bình cho tie
    n_pos, n_neg = y.sum(), (~y).sum()
    u = ranks[y].sum() - n_pos * (n_pos + 1) / 2         # số cặp (dương, âm) dương thắng, tie tính 1/2
    return float(u / (n_pos * n_neg))


def average_precision(y_true: Sequence[int], scores: Sequence[float]) -> float:
    """PR-AUC theo định nghĩa average precision (như sklearn):
    AP = sum_k (R_k - R_{k-1}) * P_k, với k chạy qua các ngưỡng là các giá trị score phân biệt,
    từ cao xuống thấp. Các ca cùng score được đưa vào cùng một lúc.
    """
    y = np.asarray(y_true).astype(float)
    s = np.asarray(scores, dtype=float)
    order = np.argsort(-s, kind="mergesort")
    y, s = y[order], s[order]
    # vị trí cuối của mỗi nhóm score bằng nhau: ngưỡng chỉ "dừng" sau khi lấy hết cả nhóm
    last = np.r_[np.flatnonzero(np.diff(s)), len(s) - 1]
    tp = np.cumsum(y)[last]
    predicted = last + 1
    precision = tp / predicted
    recall = tp / y.sum()
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


def log_loss(y_true: Sequence[int], p: Sequence[float], eps: float = 1e-15) -> float:
    """Trung bình -[y log p + (1 - y) log(1 - p)], clip p vào [eps, 1 - eps]."""
    y = np.asarray(y_true, dtype=float)
    q = np.clip(np.asarray(p, dtype=float), eps, 1 - eps)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))
