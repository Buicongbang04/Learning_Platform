"""Đạo hàm bằng tay và kiểm tra bằng sai phân hữu hạn (gradient check).

Chỉ dùng numpy. Mọi loss là trung bình trên n mẫu.
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def numerical_gradient(f: Callable[[np.ndarray], float], x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    """Gradient của f tại x bằng sai phân trung tâm: (f(x + eps eᵢ) − f(x − eps eᵢ)) / (2 eps).

    Không được sửa x của người gọi.
    """
    # TODO: lặp qua từng toạ độ i, cộng/trừ eps trên một bản sao của x
    raise NotImplementedError


def relative_error(a: np.ndarray, b: np.ndarray) -> float:
    """‖a − b‖ / (‖a‖ + ‖b‖); trả 0.0 khi cả hai bằng 0."""
    # TODO
    raise NotImplementedError


def mse_loss_grad(w: np.ndarray, X: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray]:
    """loss = mean((Xw − y)²), trả (loss, ∇_w loss)."""
    # TODO: ∇ = (2/n) Xᵀ(Xw − y)
    raise NotImplementedError


def logistic_loss_grad(w: np.ndarray, X: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray]:
    """Binary cross-entropy trung bình của p = sigmoid(Xw), y ∈ {0, 1}. Trả (loss, ∇_w loss).

    Phải ổn định số khi |Xw| rất lớn (vd. 1000): không được ra nan/inf.
    """
    # TODO: viết loss theo logit z = Xw: mean(log(1 + e^z) − y z), dùng np.logaddexp(0, z)
    # TODO: chain rule cho ∇ = (1/n) Xᵀ(sigmoid(z) − y)
    raise NotImplementedError
