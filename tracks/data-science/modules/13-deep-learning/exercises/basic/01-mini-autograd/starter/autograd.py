"""Autograd vô hướng tối giản: mỗi Value nhớ các nút cha và cách đẩy gradient về cha.

Chỉ dùng thư viện chuẩn (math). Không import torch hay numpy trong tệp này.
"""

from __future__ import annotations

import math


class Value:
    """Một số thực trong computational graph.

    data      giá trị (float)
    grad      dL/d(nút này), tính bởi backward() của nút gốc L; khởi tạo 0.0
    _parents  các nút đầu vào tạo ra nút này
    _backward hàm không tham số: cộng dồn gradient của nút này vào .grad của các nút cha
    """

    def __init__(self, data: float, _parents: tuple = (), _op: str = ""):
        self.data = float(data)
        self.grad = 0.0
        self._parents = _parents
        self._op = _op
        self._backward = lambda: None

    def __repr__(self) -> str:
        return f"Value(data={self.data:.4g}, grad={self.grad:.4g})"

    # ---- phép toán cơ bản ----------------------------------------------------------
    # Mẫu đã làm sẵn: phép cộng. Các phép khác viết theo cùng khuôn.
    def __add__(self, other: Value | float) -> Value:
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _backward():
            # d(a+b)/da = 1, d(a+b)/db = 1. Cộng dồn (+=) vì một nút có thể được dùng nhiều lần.
            self.grad += out.grad
            other.grad += out.grad

        out._backward = _backward
        return out

    def __mul__(self, other: Value | float) -> Value:
        # TODO: out = self * other, _backward theo quy tắc nhân
        raise NotImplementedError

    def __pow__(self, exponent: float) -> Value:
        """Lũy thừa với số mũ là số thực cố định (không phải Value)."""
        # TODO: d(x^k)/dx = k x^(k-1)
        raise NotImplementedError

    def exp(self) -> Value:
        # TODO
        raise NotImplementedError

    def log(self) -> Value:
        # TODO: log tự nhiên, chỉ cần đúng khi data > 0
        raise NotImplementedError

    def tanh(self) -> Value:
        # TODO: d tanh(x)/dx = 1 - tanh(x)^2
        raise NotImplementedError

    def relu(self) -> Value:
        # TODO: gradient bằng 0 khi data <= 0
        raise NotImplementedError

    # ---- các phép suy ra từ phép trên (không cần _backward riêng) -----------------
    def __neg__(self) -> Value:
        return self * -1

    def __sub__(self, other: Value | float) -> Value:
        return self + (-other)

    def __truediv__(self, other: Value | float) -> Value:
        other = other if isinstance(other, Value) else Value(other)
        return self * other ** -1

    def __radd__(self, other: float) -> Value:
        return self + other

    def __rmul__(self, other: float) -> Value:
        return self * other

    def __rsub__(self, other: float) -> Value:
        return Value(other) - self

    def __rtruediv__(self, other: float) -> Value:
        return Value(other) / self

    # ---- lan truyền ngược ----------------------------------------------------------
    def backward(self) -> None:
        """Tính gradient của nút này theo mọi nút trong graph.

        1. Sắp các nút theo thứ tự topo (cha đứng trước con) BẰNG VÒNG LẶP, không đệ quy:
           graph có thể sâu hàng nghìn tầng, vượt giới hạn đệ quy của Python.
        2. Đặt self.grad = 1.0, rồi gọi _backward() của từng nút theo thứ tự topo ĐẢO NGƯỢC.
        """
        # TODO
        raise NotImplementedError


def fit_line(xs: list[float], ys: list[float], lr: float = 0.1, steps: int = 200) -> tuple[float, float]:
    """Fit y ≈ w x + b bằng gradient descent trên MSE trung bình, dùng Value để lấy gradient.

    Bắt đầu từ w = b = 0. Mỗi bước: dựng loss = mean((w x + b - y)^2) bằng Value, backward,
    cập nhật w.data -= lr * w.grad (tương tự b), rồi đặt lại grad = 0 trước bước sau.
    Trả về (w, b) dạng float.
    """
    # TODO
    raise NotImplementedError
