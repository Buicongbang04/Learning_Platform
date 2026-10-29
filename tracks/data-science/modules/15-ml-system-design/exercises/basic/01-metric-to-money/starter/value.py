"""Đổi metric model ra tiền: confusion, expected value, break-even precision, ngưỡng tối ưu theo giá trị."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def confusion_counts(y_true: Sequence[int], p: Sequence[float], threshold: float) -> dict[str, int]:
    """Dự đoán dương khi p >= threshold. Trả dict tp, fp, fn, tn (int)."""
    # TODO
    raise NotImplementedError


def expected_value(y_true: Sequence[int], p: Sequence[float], threshold: float,
                   cost_action: float, loss_event: float, effect: float) -> float:
    """Tổng giá trị (R$) so với không làm gì: TP → effect*loss_event − cost_action, FP → −cost_action."""
    # TODO: dùng confusion_counts
    raise NotImplementedError


def break_even_precision(cost_action: float, loss_event: float, effect: float) -> float:
    """Precision tối thiểu để hành động có lãi. Có thể > 1 (không bao giờ có lãi)."""
    # TODO
    raise NotImplementedError


def best_threshold_value(y_true: Sequence[int], p: Sequence[float], cost_action: float,
                         loss_event: float, effect: float) -> tuple[float, float]:
    """(threshold, value) làm expected_value lớn nhất; ứng viên: mọi p phân biệt và np.inf (value 0)."""
    # TODO
    raise NotImplementedError
