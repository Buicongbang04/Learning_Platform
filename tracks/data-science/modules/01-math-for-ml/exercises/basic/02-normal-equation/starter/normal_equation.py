"""Linear regression bằng normal equation: XᵀX w = Xᵀy.

Chỉ dùng numpy. Không dùng np.linalg.inv / pinv / lstsq trong fit_normal_equation.
"""

from __future__ import annotations

import numpy as np


def add_intercept(X: np.ndarray) -> np.ndarray:
    """Thêm cột toàn 1 vào bên trái X (n×d → n×(d+1)). Không sửa X gốc."""
    # TODO: np.column_stack
    raise NotImplementedError


def fit_normal_equation(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Hệ số w (độ dài = số cột của X) cực tiểu ‖y − Xw‖². X đã có cột intercept nếu cần."""
    # TODO: giải hệ (XᵀX) w = Xᵀy bằng np.linalg.solve
    raise NotImplementedError


def predict(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    """ŷ = Xw."""
    # TODO
    raise NotImplementedError


def r2_score(y: np.ndarray, y_pred: np.ndarray) -> float:
    """R² = 1 − SS_res / SS_tot, với SS_tot tính quanh trung bình của y."""
    # TODO
    raise NotImplementedError
