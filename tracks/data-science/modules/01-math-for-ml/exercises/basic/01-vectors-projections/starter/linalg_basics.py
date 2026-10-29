"""Vector, phép chiếu và condition number: những phép toán đứng sau linear regression.

Chỉ dùng numpy. Không dùng np.linalg.inv: giải hệ bằng np.linalg.solve.
"""

from __future__ import annotations

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """cos của góc giữa a và b: a·b / (‖a‖ ‖b‖). Nằm trong [-1, 1]."""
    # TODO
    raise NotImplementedError


def project_onto_vector(v: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Hình chiếu vuông góc của v lên đường thẳng sinh bởi u: (v·u / u·u) u."""
    # TODO
    raise NotImplementedError


def projection_matrix(X: np.ndarray) -> np.ndarray:
    """Ma trận chiếu lên không gian cột của X (n×d, các cột độc lập): P = X (XᵀX)⁻¹ Xᵀ.

    Không tính nghịch đảo: giải (XᵀX) B = Xᵀ bằng np.linalg.solve rồi P = X B.
    """
    # TODO
    raise NotImplementedError


def condition_number(X: np.ndarray) -> float:
    """Condition number theo chuẩn 2: σ_max / σ_min, từ các singular value của X."""
    # TODO: np.linalg.svd(X, compute_uv=False)
    raise NotImplementedError
