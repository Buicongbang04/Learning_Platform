"""Đổi metric model ra tiền: confusion, expected value, break-even precision, ngưỡng tối ưu theo giá trị."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def confusion_counts(y_true: Sequence[int], p: Sequence[float], threshold: float) -> dict[str, int]:
    """Dự đoán dương khi p >= threshold. Trả dict tp, fp, fn, tn (int)."""
    y = np.asarray(y_true).astype(bool)
    pred = np.asarray(p, dtype=float) >= threshold
    return {"tp": int(np.sum(y & pred)), "fp": int(np.sum(~y & pred)),
            "fn": int(np.sum(y & ~pred)), "tn": int(np.sum(~y & ~pred))}


def expected_value(y_true: Sequence[int], p: Sequence[float], threshold: float,
                   cost_action: float, loss_event: float, effect: float) -> float:
    """Tổng giá trị (R$) so với không làm gì: TP → effect*loss_event − cost_action, FP → −cost_action."""
    c = confusion_counts(y_true, p, threshold)
    return float(c["tp"] * (effect * loss_event - cost_action) - c["fp"] * cost_action)


def break_even_precision(cost_action: float, loss_event: float, effect: float) -> float:
    """Precision tối thiểu để hành động có lãi. Có thể > 1 (không bao giờ có lãi)."""
    return cost_action / (effect * loss_event)


def best_threshold_value(y_true: Sequence[int], p: Sequence[float], cost_action: float,
                         loss_event: float, effect: float) -> tuple[float, float]:
    """(threshold, value) làm expected_value lớn nhất; ứng viên: mọi p phân biệt và np.inf (value 0)."""
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(p, dtype=float)
    order = np.argsort(-p, kind="stable")
    p_sorted, y_sorted = p[order], y[order]
    tp = np.cumsum(y_sorted)
    k = np.arange(1, len(p) + 1)
    values = tp * (effect * loss_event - cost_action) - (k - tp) * cost_action
    # chọn ngưỡng t là chọn mọi đơn có p >= t: chỉ xét vị trí cuối của mỗi nhóm p bằng nhau
    last_of_group = np.r_[p_sorted[1:] != p_sorted[:-1], True]
    values, thresholds = values[last_of_group], p_sorted[last_of_group]
    best_t, best_v = np.inf, 0.0
    if len(values) and values.max() > 0:
        i = int(np.argmax(values))
        best_t, best_v = float(thresholds[i]), float(values[i])
    return best_t, best_v
