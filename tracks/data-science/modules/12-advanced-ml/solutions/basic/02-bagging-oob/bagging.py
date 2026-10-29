"""Bagging cây hồi quy viết tay, kèm out-of-bag (OOB) estimate."""

from __future__ import annotations

import numpy as np
from sklearn.tree import DecisionTreeRegressor


def expected_oob_fraction(n: int) -> float:
    """Xác suất một điểm KHÔNG được chọn vào một mẫu bootstrap cỡ n: (1 − 1/n)^n."""
    return float((1 - 1 / n) ** n)


def bagging_fit_predict(X_train, y_train, X_test, n_estimators: int = 100, seed: int = 0,
                        max_features: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Trả (test_pred, oob_pred).

    Mỗi cây: rng.integers(0, n, n) làm chỉ số bootstrap (rng = np.random.default_rng(seed)),
    DecisionTreeRegressor(max_features=max_features, random_state=<số nguyên từ rng>) không giới hạn
    độ sâu. test_pred: trung bình dự đoán của mọi cây. oob_pred[i]: trung bình dự đoán của các cây
    KHÔNG có điểm i trong mẫu bootstrap; NaN nếu điểm i có mặt trong mọi mẫu.
    """
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train, dtype=float)
    X_test = np.asarray(X_test, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(y_train)
    test_sum = np.zeros(len(X_test))
    oob_sum = np.zeros(n)
    oob_count = np.zeros(n)
    for _ in range(n_estimators):
        idx = rng.integers(0, n, n)
        tree = DecisionTreeRegressor(max_features=max_features,
                                     random_state=int(rng.integers(2**31 - 1)))
        tree.fit(X_train[idx], y_train[idx])
        test_sum += tree.predict(X_test)
        out = np.ones(n, dtype=bool)
        out[idx] = False
        if out.any():
            oob_sum[out] += tree.predict(X_train[out])
            oob_count[out] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        oob_pred = np.where(oob_count > 0, oob_sum / oob_count, np.nan)
    return test_sum / n_estimators, oob_pred
