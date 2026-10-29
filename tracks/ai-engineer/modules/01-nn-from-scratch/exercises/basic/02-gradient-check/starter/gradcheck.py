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
    # TODO
    raise NotImplementedError


def relative_error(a: np.ndarray, b: np.ndarray) -> float:
    """max|a - b| / max(max|a| + max|b|, 1e-12), trả về float Python."""
    # TODO
    raise NotImplementedError
