"""Chính sách liên hệ chủ động: ngưỡng theo chi phí có giới hạn năng lực CSKH, và khoảng tin cậy của khoản tiết kiệm."""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np


def capacity_threshold(y_true: Sequence[int], p: Sequence[float], costs: Mapping[str, float],
                       max_contact_rate: float) -> float:
    """Ngưỡng t làm chi phí trung bình nhỏ nhất (dự đoán dương khi p >= t), với ràng buộc
    tỉ lệ đơn được liên hệ mean(p >= t) <= max_contact_rate.

    costs có khoá "tp", "fp", "fn", "tn" (thiếu thì 0). Ứng viên: mọi giá trị p phân biệt và np.inf.
    """
    # TODO
    raise NotImplementedError


def bootstrap_saving(y_true: Sequence[int], p: Sequence[float], threshold: float, costs: Mapping[str, float],
                     n_boot: int = 1000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float, float]:
    """(saving, lo, hi): saving = chi phí/đơn khi không liên hệ ai − chi phí/đơn của chính sách,
    tính trên dữ liệu gốc; [lo, hi] là percentile bootstrap (resample đơn có hoàn lại, n_boot lần,
    np.random.default_rng(seed)).
    """
    # TODO
    raise NotImplementedError
