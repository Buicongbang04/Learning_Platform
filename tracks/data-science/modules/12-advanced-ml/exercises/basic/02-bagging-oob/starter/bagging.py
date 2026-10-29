"""Bagging cây hồi quy viết tay, kèm out-of-bag (OOB) estimate."""

from __future__ import annotations

import numpy as np
from sklearn.tree import DecisionTreeRegressor


def expected_oob_fraction(n: int) -> float:
    """Xác suất một điểm KHÔNG được chọn vào một mẫu bootstrap cỡ n."""
    # TODO: mỗi lần rút, điểm i không được chọn với xác suất 1 − 1/n; rút n lần độc lập
    raise NotImplementedError


def bagging_fit_predict(X_train, y_train, X_test, n_estimators: int = 100, seed: int = 0,
                        max_features: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Trả (test_pred, oob_pred).

    Mỗi cây: rng.integers(0, n, n) làm chỉ số bootstrap (rng = np.random.default_rng(seed)),
    DecisionTreeRegressor(max_features=max_features, random_state=<số nguyên từ rng>) không giới hạn
    độ sâu. test_pred: trung bình dự đoán của mọi cây. oob_pred[i]: trung bình dự đoán của các cây
    KHÔNG có điểm i trong mẫu bootstrap; NaN nếu điểm i có mặt trong mọi mẫu.
    """
    # TODO: rng = np.random.default_rng(seed); với mỗi cây: chỉ số bootstrap, random_state từ rng
    # TODO: cộng dồn dự đoán test; với điểm ngoài mẫu (out-of-bag) cộng dồn dự đoán và đếm số cây
    # TODO: oob_pred = tổng / số cây, NaN nếu số cây = 0
    raise NotImplementedError
