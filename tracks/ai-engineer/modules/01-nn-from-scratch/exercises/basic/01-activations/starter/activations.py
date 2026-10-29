"""Activation, đạo hàm và softmax, viết bằng numpy.

Mọi hàm nhận một np.ndarray float64 bất kỳ shape và trả mảng cùng shape (tính từng phần tử,
trừ softmax). Đạo hàm `*_grad(x)` là đạo hàm của activation theo chính input `x`.
Chỉ dùng numpy trong tệp này (test dùng torch để đối chiếu).
"""

from __future__ import annotations

import numpy as np


def sigmoid(x: np.ndarray) -> np.ndarray:
    """1 / (1 + e^-x). Phải chạy với x = ±1000 mà không tràn số (overflow)."""
    # TODO
    raise NotImplementedError


def sigmoid_grad(x: np.ndarray) -> np.ndarray:
    """dσ/dx tại x."""
    # TODO
    raise NotImplementedError


def tanh(x: np.ndarray) -> np.ndarray:
    # TODO: được dùng np.tanh
    raise NotImplementedError


def tanh_grad(x: np.ndarray) -> np.ndarray:
    # TODO
    raise NotImplementedError


def relu(x: np.ndarray) -> np.ndarray:
    # TODO
    raise NotImplementedError


def relu_grad(x: np.ndarray) -> np.ndarray:
    """Quy ước như mọi framework: đạo hàm tại đúng x = 0 bằng 0."""
    # TODO
    raise NotImplementedError


def gelu(x: np.ndarray) -> np.ndarray:
    """GELU bản xấp xỉ tanh (GPT-2, torch gelu(approximate="tanh")), công thức ở mục 2 lý thuyết."""
    # TODO
    raise NotImplementedError


def gelu_grad(x: np.ndarray) -> np.ndarray:
    """Đạo hàm của đúng bản xấp xỉ tanh ở trên (không phải của x·Φ(x))."""
    # TODO
    raise NotImplementedError


def softmax(z: np.ndarray, axis: int = -1) -> np.ndarray:
    """Softmax theo trục `axis`, ổn định số: logits cỡ 1000 không ra nan."""
    # TODO
    raise NotImplementedError
