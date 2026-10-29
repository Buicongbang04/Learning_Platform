"""Hai phép kiểm nhanh để bắt leakage trước khi train model."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def single_feature_auc(X: pd.DataFrame, y) -> pd.Series:
    """AUC khi dùng riêng từng cột số làm điểm dự đoán, lấy max(AUC, 1 − AUC).

    Bỏ các dòng NaN của cột đang xét. Cột hằng (hoặc chỉ một lớp sau khi bỏ NaN) cho 0.5.
    Trả Series index là tên cột, sắp giảm dần.
    """
    # TODO: lặp qua từng cột, roc_auc_score(y, x) trên các dòng không NaN
    raise NotImplementedError


def suspicious_features(X: pd.DataFrame, y, threshold: float = 0.9) -> list[str]:
    """Tên các cột có single_feature_auc >= threshold, theo thứ tự AUC giảm dần."""
    # TODO
    raise NotImplementedError


def available_after(df: pd.DataFrame, known_at: dict[str, str], prediction_col: str) -> pd.Series:
    """Tỉ lệ dòng mà feature chỉ biết được SAU thời điểm dự đoán.

    known_at: {tên feature: tên cột thời điểm feature đó được ghi nhận}. Ví dụ ngày hẹn giao
    (order_estimated_delivery_date) có giá trị là một ngày tương lai nhưng được ghi nhận lúc mua,
    nên known_at của nó là order_purchase_timestamp.
    Chỉ tính trên các dòng có cả hai mốc; so sánh chặt (>). Trả Series index là các feature.
    """
    # TODO
    raise NotImplementedError
