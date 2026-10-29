"""Chọn ngưỡng phân loại theo ma trận chi phí thay vì mặc định 0.5."""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np


def _cells(costs: Mapping[str, float]) -> tuple[float, float, float, float]:
    return tuple(float(costs.get(k, 0.0)) for k in ("tp", "fp", "fn", "tn"))


def expected_cost(y_true: Sequence[int], p: Sequence[float], threshold: float,
                  costs: Mapping[str, float]) -> float:
    """Chi phí trung bình mỗi mẫu khi dự đoán dương nếu p >= threshold.

    costs có các khoá "tp", "fp", "fn", "tn"; khoá thiếu được coi là 0.
    """
    y = np.asarray(y_true).astype(bool)
    pred = np.asarray(p, dtype=float) >= threshold
    c_tp, c_fp, c_fn, c_tn = _cells(costs)
    total = (c_tp * np.sum(y & pred) + c_fp * np.sum(~y & pred)
             + c_fn * np.sum(y & ~pred) + c_tn * np.sum(~y & ~pred))
    return float(total / len(y))


def bayes_threshold(costs: Mapping[str, float]) -> float:
    """Ngưỡng tối ưu lý thuyết khi p đã calibrate:
    dự đoán dương khi p * C_TP + (1 - p) * C_FP <= p * C_FN + (1 - p) * C_TN.
    """
    c_tp, c_fp, c_fn, c_tn = _cells(costs)
    return (c_fp - c_tn) / ((c_fp - c_tn) + (c_fn - c_tp))


def best_threshold(y_true: Sequence[int], p: Sequence[float], costs: Mapping[str, float]) -> float:
    """Ngưỡng làm expected_cost nhỏ nhất trên chính dữ liệu này (thường là tập validation).

    Ứng viên là mọi giá trị p phân biệt, cộng thêm np.inf (không dự đoán dương ca nào).
    """
    y = np.asarray(y_true).astype(bool)
    p = np.asarray(p, dtype=float)
    c_tp, c_fp, c_fn, c_tn = _cells(costs)
    # Vector hoá: sắp p giảm dần; ngưỡng = giá trị p thứ k nghĩa là lấy mọi ca có p >= giá trị đó.
    order = np.argsort(-p, kind="mergesort")
    ps, ys = p[order], y[order]
    last = np.r_[np.flatnonzero(np.diff(ps)), len(ps) - 1]       # cuối mỗi nhóm p bằng nhau
    tp = np.cumsum(ys)[last]
    fp = (last + 1) - tp
    fn = ys.sum() - tp
    tn = (~ys).sum() - fp
    cost = c_tp * tp + c_fp * fp + c_fn * fn + c_tn * tn
    none = c_fn * ys.sum() + c_tn * (~ys).sum()                   # ngưỡng inf: không ai dương
    candidates = np.r_[ps[last], np.inf]
    return float(candidates[np.argmin(np.r_[cost, none])])
