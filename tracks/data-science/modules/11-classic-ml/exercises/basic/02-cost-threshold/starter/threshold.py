"""Chọn ngưỡng phân loại theo ma trận chi phí thay vì mặc định 0.5."""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np


def expected_cost(y_true: Sequence[int], p: Sequence[float], threshold: float,
                  costs: Mapping[str, float]) -> float:
    """Chi phí trung bình mỗi mẫu khi dự đoán dương nếu p >= threshold.

    costs có các khoá "tp", "fp", "fn", "tn"; khoá thiếu được coi là 0.
    """
    # TODO: đếm 4 ô, nhân với chi phí, chia cho số mẫu
    raise NotImplementedError


def bayes_threshold(costs: Mapping[str, float]) -> float:
    """Ngưỡng tối ưu lý thuyết khi p đã calibrate:
    dự đoán dương khi p * C_TP + (1 - p) * C_FP <= p * C_FN + (1 - p) * C_TN.
    """
    # TODO: giải bất phương trình theo p
    raise NotImplementedError


def best_threshold(y_true: Sequence[int], p: Sequence[float], costs: Mapping[str, float]) -> float:
    """Ngưỡng làm expected_cost nhỏ nhất trên chính dữ liệu này (thường là tập validation).

    Ứng viên là mọi giá trị p phân biệt, cộng thêm np.inf (không dự đoán dương ca nào).
    """
    # TODO
    raise NotImplementedError
