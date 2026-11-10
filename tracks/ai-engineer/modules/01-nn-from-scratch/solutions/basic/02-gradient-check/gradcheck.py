"""Gradient check: gradient số bằng sai phân trung tâm và sai số tương đối.

Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def numerical_grad(f: Callable[[np.ndarray], float], x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Gradient của hàm vô hướng f tại x, tính từng phần tử bằng sai phân trung tâm.

    x có thể có shape bất kỳ; kết quả cùng shape với x. Mỗi lần gọi f chỉ một phần tử của x bị
    dịch đi ±eps. Khi hàm trả về, x phải giống hệt lúc gọi (từng bit).
    """
    grad = np.zeros_like(x, dtype=float)
    for idx in np.ndindex(x.shape):
        old = x[idx]
        try:
            x[idx] = old + eps
            f_plus = f(x)
            x[idx] = old - eps
            f_minus = f(x)
        finally:
            x[idx] = old  # gán lại đúng giá trị gốc; (old + eps) - eps chưa chắc bằng old
        grad[idx] = (f_plus - f_minus) / (2 * eps)
    return grad


def relative_error(a: np.ndarray, b: np.ndarray) -> float:
    """max|a - b| / max(max|a| + max|b|, 1e-12), trả về float Python."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    num = np.max(np.abs(a - b))
    den = max(np.max(np.abs(a)) + np.max(np.abs(b)), 1e-12)
    return float(num / den)
