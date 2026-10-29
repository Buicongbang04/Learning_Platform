"""Bốn cách giải least squares, và chẩn đoán khi nào ma trận "xấu".

Mọi hàm giải nhận X (n×d, cột 0 là intercept nếu có) và y (n), trả w (d).
Được dùng numpy và scipy.linalg. Không dùng np.linalg.lstsq / pinv trong lời giải (test dùng chúng
làm đáp án tham chiếu).
"""

from __future__ import annotations

import numpy as np


def polynomial_features(x: np.ndarray, degree: int) -> np.ndarray:
    """Ma trận [1, x, x², ..., x^degree] (n×(degree+1))."""
    # TODO
    raise NotImplementedError


def solve_normal(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Normal equation: giải (XᵀX) w = Xᵀy."""
    # TODO
    raise NotImplementedError


def solve_qr(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """X = QR (reduced), rồi giải hệ tam giác R w = Qᵀy (scipy.linalg.solve_triangular)."""
    # TODO
    raise NotImplementedError


def solve_svd(X: np.ndarray, y: np.ndarray, rcond: float = 1e-10) -> np.ndarray:
    """X = U Σ Vᵀ; chỉ giữ σᵢ > rcond · σ_max; w = Σᵢ vᵢ (uᵢᵀy) / σᵢ.

    Khi X thiếu hạng (rank-deficient), đây là nghiệm có ‖w‖ nhỏ nhất trong mọi nghiệm least squares.
    """
    # TODO
    raise NotImplementedError


def ridge(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """Cực tiểu ‖y − Xw‖² + lam · Σ_{j≥1} wⱼ²: KHÔNG phạt intercept (cột 0)."""
    # TODO
    raise NotImplementedError


def scaled_condition_number(X: np.ndarray) -> float:
    """Condition number sau khi chia mỗi cột cho chuẩn L2 của nó.

    Phần ill-conditioning còn lại sau bước này là do các cột gần phụ thuộc tuyến tính, không phải
    do đơn vị đo.
    """
    # TODO
    raise NotImplementedError
