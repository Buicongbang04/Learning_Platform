"""Vector, phép chiếu và condition number: những phép toán đứng sau linear regression.

Chỉ dùng numpy. Không dùng np.linalg.inv: giải hệ bằng np.linalg.solve.
"""

from __future__ import annotations

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """cos của góc giữa a và b: a·b / (‖a‖ ‖b‖). Nằm trong [-1, 1]."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def project_onto_vector(v: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Hình chiếu vuông góc của v lên đường thẳng sinh bởi u: (v·u / u·u) u."""
    v, u = np.asarray(v, dtype=float), np.asarray(u, dtype=float)
    return (v @ u) / (u @ u) * u


def projection_matrix(X: np.ndarray) -> np.ndarray:
    """Ma trận chiếu lên không gian cột của X (n×d, các cột độc lập): P = X (XᵀX)⁻¹ Xᵀ.

    Không tính nghịch đảo: giải (XᵀX) B = Xᵀ bằng np.linalg.solve rồi P = X B.
    """
    X = np.asarray(X, dtype=float)
    B = np.linalg.solve(X.T @ X, X.T)     # d×n, chính là (XᵀX)⁻¹Xᵀ
    return X @ B


def condition_number(X: np.ndarray) -> float:
    """Condition number theo chuẩn 2: σ_max / σ_min, từ các singular value của X."""
    s = np.linalg.svd(np.asarray(X, dtype=float), compute_uv=False)
    return float(s[0] / s[-1])
