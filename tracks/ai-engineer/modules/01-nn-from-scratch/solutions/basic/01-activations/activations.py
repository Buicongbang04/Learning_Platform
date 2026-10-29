"""Activation, đạo hàm và softmax, viết bằng numpy.

Mọi hàm nhận một np.ndarray float64 bất kỳ shape và trả mảng cùng shape (tính từng phần tử,
trừ softmax). Đạo hàm `*_grad(x)` là đạo hàm của activation theo chính input `x`.
Chỉ dùng numpy trong tệp này (test dùng torch để đối chiếu).
"""

from __future__ import annotations

import numpy as np

_GELU_C = np.sqrt(2.0 / np.pi)
_GELU_A = 0.044715


def sigmoid(x: np.ndarray) -> np.ndarray:
    """1 / (1 + e^-x). Phải chạy với x = ±1000 mà không tràn số (overflow)."""
    x = np.asarray(x, dtype=float)
    # e = e^{-|x|} luôn trong (0, 1]: không bao giờ tràn, cùng lắm underflow về 0.
    e = np.exp(-np.abs(x))
    # x >= 0: 1 / (1 + e^{-x});  x < 0: e^{x} / (1 + e^{x}) (nhân tử và mẫu với e^{x}).
    return np.where(x >= 0, 1.0 / (1.0 + e), e / (1.0 + e))


def sigmoid_grad(x: np.ndarray) -> np.ndarray:
    """dσ/dx tại x."""
    s = sigmoid(x)
    return s * (1.0 - s)


def tanh(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


def tanh_grad(x: np.ndarray) -> np.ndarray:
    t = np.tanh(x)
    return 1.0 - t * t


def relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


def relu_grad(x: np.ndarray) -> np.ndarray:
    """Quy ước như mọi framework: đạo hàm tại đúng x = 0 bằng 0."""
    return (np.asarray(x) > 0).astype(float)


def gelu(x: np.ndarray) -> np.ndarray:
    """GELU bản xấp xỉ tanh (GPT-2, torch gelu(approximate="tanh")), công thức ở mục 2 lý thuyết."""
    u = _GELU_C * (x + _GELU_A * x**3)
    return 0.5 * x * (1.0 + np.tanh(u))


def gelu_grad(x: np.ndarray) -> np.ndarray:
    """Đạo hàm của đúng bản xấp xỉ tanh ở trên (không phải của x·Φ(x))."""
    u = _GELU_C * (x + _GELU_A * x**3)
    t = np.tanh(u)
    du = _GELU_C * (1.0 + 3.0 * _GELU_A * x**2)
    # quy tắc tích: d/dx [0.5 x] * (1 + t)  +  0.5 x * d/dx [1 + tanh(u)]
    return 0.5 * (1.0 + t) + 0.5 * x * (1.0 - t * t) * du


def softmax(z: np.ndarray, axis: int = -1) -> np.ndarray:
    """Softmax theo trục `axis`, ổn định số: logits cỡ 1000 không ra nan."""
    # trừ max theo đúng trục: số mũ lớn nhất của mỗi dòng là e^0 = 1, mẫu số >= 1
    e = np.exp(z - z.max(axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)
