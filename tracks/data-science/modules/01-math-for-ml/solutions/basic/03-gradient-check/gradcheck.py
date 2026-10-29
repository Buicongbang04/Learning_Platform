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
    x = np.array(x, dtype=float)          # bản sao
    grad = np.zeros_like(x)
    for i in range(x.size):
        old = x.flat[i]
        x.flat[i] = old + eps
        f_plus = f(x)
        x.flat[i] = old - eps
        f_minus = f(x)
        x.flat[i] = old
        grad.flat[i] = (f_plus - f_minus) / (2 * eps)
    return grad


def relative_error(a: np.ndarray, b: np.ndarray) -> float:
    """‖a − b‖ / (‖a‖ + ‖b‖); trả 0.0 khi cả hai bằng 0."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denom = np.linalg.norm(a) + np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.linalg.norm(a - b) / denom)


def mse_loss_grad(w: np.ndarray, X: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray]:
    """loss = mean((Xw − y)²), trả (loss, ∇_w loss)."""
    r = X @ w - y
    return float(np.mean(r ** 2)), 2 * X.T @ r / len(y)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    # exp(-logaddexp(0, -z)) = 1 / (1 + e^{-z}), không tràn số ở cả hai phía
    return np.exp(-np.logaddexp(0.0, -z))


def logistic_loss_grad(w: np.ndarray, X: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray]:
    """Binary cross-entropy trung bình của p = sigmoid(Xw), y ∈ {0, 1}. Trả (loss, ∇_w loss).

    Phải ổn định số khi |Xw| rất lớn (vd. 1000): không được ra nan/inf.
    """
    z = X @ w
    # −[y log σ(z) + (1 − y) log(1 − σ(z))] = log(1 + e^z) − y z
    loss = np.mean(np.logaddexp(0.0, z) - y * z)
    grad = X.T @ (_sigmoid(z) - y) / len(y)
    return float(loss), grad
