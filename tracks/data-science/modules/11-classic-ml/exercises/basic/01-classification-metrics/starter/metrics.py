"""Metric phân loại tự cài bằng numpy: confusion, precision/recall/F1, ROC-AUC, PR-AUC, log loss.

Không dùng sklearn trong tệp này. Test so kết quả với sklearn.metrics.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np


def confusion_counts(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, int]:
    """Trả {"tp": ..., "fp": ..., "fn": ..., "tn": ...} (int thường) cho nhãn 0/1."""
    # TODO
    raise NotImplementedError


def precision_recall_f1(y_true: Sequence[int], y_pred: Sequence[int]) -> tuple[float, float, float]:
    """(precision, recall, f1). Mẫu số bằng 0 thì trả 0.0 cho đại lượng đó."""
    # TODO: dùng confusion_counts
    raise NotImplementedError


def roc_auc(y_true: Sequence[int], scores: Sequence[float]) -> float:
    """ROC-AUC = P(score của một ca dương ngẫu nhiên > score của một ca âm ngẫu nhiên),
    tính điểm trùng (tie) là 1/2. Cài bằng thứ hạng (Mann-Whitney), O(n log n), không lặp đôi một.
    """
    # TODO: xếp hạng scores (hạng trung bình cho tie), cộng hạng của ca dương
    raise NotImplementedError


def average_precision(y_true: Sequence[int], scores: Sequence[float]) -> float:
    """PR-AUC theo định nghĩa average precision (như sklearn):
    AP = sum_k (R_k - R_{k-1}) * P_k, với k chạy qua các ngưỡng là các giá trị score phân biệt,
    từ cao xuống thấp. Các ca cùng score được đưa vào cùng một lúc.
    """
    # TODO
    raise NotImplementedError


def log_loss(y_true: Sequence[int], p: Sequence[float], eps: float = 1e-15) -> float:
    """Trung bình -[y log p + (1 - y) log(1 - p)], clip p vào [eps, 1 - eps]."""
    # TODO
    raise NotImplementedError
