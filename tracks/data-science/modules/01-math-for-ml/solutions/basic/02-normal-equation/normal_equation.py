"""Linear regression bằng normal equation: XᵀX w = Xᵀy.

Chỉ dùng numpy. Không dùng np.linalg.inv / pinv / lstsq trong fit_normal_equation.
"""

from __future__ import annotations

import numpy as np


def add_intercept(X: np.ndarray) -> np.ndarray:
    """Thêm cột toàn 1 vào bên trái X (n×d → n×(d+1)). Không sửa X gốc."""
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    return np.column_stack([np.ones(len(X)), X])


def fit_normal_equation(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Hệ số w (độ dài = số cột của X) cực tiểu ‖y − Xw‖². X đã có cột intercept nếu cần."""
    X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=float)
    return np.linalg.solve(X.T @ X, X.T @ y)


def predict(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    """ŷ = Xw."""
    return np.asarray(X, dtype=float) @ w


def r2_score(y: np.ndarray, y_pred: np.ndarray) -> float:
    """R² = 1 − SS_res / SS_tot, với SS_tot tính quanh trung bình của y."""
    y, y_pred = np.asarray(y, dtype=float), np.asarray(y_pred, dtype=float)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return float(1 - ss_res / ss_tot)
