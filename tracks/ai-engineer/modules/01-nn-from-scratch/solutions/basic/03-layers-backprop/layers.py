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
        self.W = rng.normal(0.0, np.sqrt(2.0 / in_features), (in_features, out_features))
        self.b = np.zeros(out_features)
        self.dW: np.ndarray | None = None
        self.db: np.ndarray | None = None
        self.x: np.ndarray | None = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.x = x
        return x @ self.W + self.b

    def backward(self, grad: np.ndarray) -> np.ndarray:
        """grad = dL/d(out), shape (N, out). Gán self.dW, self.db, trả dL/dx shape (N, in)."""
        self.dW = self.x.T @ grad          # (in, N) @ (N, out) -> (in, out), cùng shape W
        self.db = grad.sum(axis=0)         # b broadcast cho N dòng khi forward -> cộng theo batch
        return grad @ self.W.T             # (N, out) @ (out, in) -> (N, in)


class ReLU:
    def __init__(self):
        self.mask: np.ndarray | None = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.mask = x > 0
        return np.where(self.mask, x, 0.0)

    def backward(self, grad: np.ndarray) -> np.ndarray:
        return grad * self.mask            # tại đúng 0: mask False -> gradient 0


class SoftmaxCrossEntropy:
    """Softmax + cross-entropy gộp một layer: nhận logits, trả loss trung bình trên batch."""

    def __init__(self):
        self.probs: np.ndarray | None = None
        self.y: np.ndarray | None = None

    def forward(self, logits: np.ndarray, y: np.ndarray) -> float:
        """logits shape (N, C), y là mảng int shape (N,) chứa nhãn lớp 0..C-1. Trả float Python.

        Phải ổn định số: logits cỡ 1000 không ra inf/nan.
        """
        z = logits - logits.max(axis=1, keepdims=True)
        log_p = z - np.log(np.exp(z).sum(axis=1, keepdims=True))   # log-softmax, không log(0)
        self.probs = np.exp(log_p)
        self.y = np.asarray(y)
        return float(-log_p[np.arange(len(self.y)), self.y].mean())

    def backward(self) -> np.ndarray:
        """dL/dlogits, shape (N, C). Không nhận tham số: loss là điểm cuối của graph."""
        n = len(self.y)
        d = self.probs.copy()              # copy: không làm hỏng probs đã cache
        d[np.arange(n), self.y] -= 1.0     # p - onehot(y)
        return d / n                       # chia N vì loss là trung bình
