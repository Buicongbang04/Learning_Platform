"""Layer có forward/backward, viết bằng numpy: một nn.Module thu nhỏ.

Quy ước (giống phần lý thuyết): batch theo dòng, x shape (N, in), W shape (in, out), out = x @ W + b.
forward lưu lại (cache) những gì backward cần. backward nhận dL/d(output) và trả dL/d(input).
Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import numpy as np


class Linear:
    """out = x @ W + b.

    W   shape (in_features, out_features), khởi tạo He: phân phối chuẩn, trung bình 0, phương sai 2 / in_features
    b   shape (out_features,), khởi tạo 0
    dW, db  gradient của loss theo W, b; được GÁN (không cộng dồn) mỗi lần gọi backward
    """

    def __init__(self, in_features: int, out_features: int, rng: np.random.Generator):
        # TODO: tạo self.W, self.b; mọi số ngẫu nhiên lấy từ `rng` (không dùng np.random toàn cục)
        self.dW: np.ndarray | None = None
        self.db: np.ndarray | None = None
        raise NotImplementedError

    def forward(self, x: np.ndarray) -> np.ndarray:
        # TODO: lưu x để backward dùng
        raise NotImplementedError

    def backward(self, grad: np.ndarray) -> np.ndarray:
        """grad = dL/d(out), shape (N, out). Gán self.dW, self.db, trả dL/dx shape (N, in)."""
        # TODO
        raise NotImplementedError


class ReLU:
    def __init__(self):
        self.mask: np.ndarray | None = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        # TODO
        raise NotImplementedError

    def backward(self, grad: np.ndarray) -> np.ndarray:
        # TODO: đạo hàm tại đúng 0 quy ước bằng 0
        raise NotImplementedError


class SoftmaxCrossEntropy:
    """Softmax + cross-entropy gộp một layer: nhận logits, trả loss trung bình trên batch."""

    def __init__(self):
        self.probs: np.ndarray | None = None
        self.y: np.ndarray | None = None

    def forward(self, logits: np.ndarray, y: np.ndarray) -> float:
        """logits shape (N, C), y là mảng int shape (N,) chứa nhãn lớp 0..C-1. Trả float Python.

        Phải ổn định số: logits cỡ 1000 không ra inf/nan.
        """
        # TODO
        raise NotImplementedError

    def backward(self) -> np.ndarray:
        """dL/dlogits, shape (N, C). Không nhận tham số: loss là điểm cuối của graph."""
        # TODO
        raise NotImplementedError
