"""Conv2d bằng numpy: im2col, col2im, forward và backward.

Quy ước giống PyTorch (NCHW):
    x    shape (N, C, H, W)            batch ảnh
    W    shape (F, C, kh, kw)          F bộ lọc
    b    shape (F,)
    out  shape (N, F, OH, OW),  OH = (H + 2*padding - kh) // stride + 1  (OW tương tự)

im2col trải mỗi "cửa sổ" C x kh x kw mà bộ lọc nhìn thấy thành một dòng, để conv thành một phép nhân ma trận:
    cols shape (N*OH*OW, C*kh*kw); dòng theo thứ tự (n, oh, ow), cột theo thứ tự (c, i, j),
    tức cùng thứ tự với W.reshape(F, -1).
Chỉ dùng numpy trong tệp này. Không vòng lặp Python qua N, OH, OW (chậm hàng trăm lần);
được phép lặp qua kh, kw.
"""

from __future__ import annotations

import numpy as np


def output_size(n: int, k: int, stride: int, padding: int) -> int:
    return (n + 2 * padding - k) // stride + 1


def im2col(x: np.ndarray, kh: int, kw: int, stride: int = 1, padding: int = 0) -> np.ndarray:
    """x (N, C, H, W) → cols (N*OH*OW, C*kh*kw). Vùng padding là số 0."""
    N, C, H, W = x.shape
    OH, OW = output_size(H, kh, stride, padding), output_size(W, kw, stride, padding)
    xp = np.pad(x, ((0, 0), (0, 0), (padding, padding), (padding, padding)))
    cols = np.empty((N, C, kh, kw, OH, OW), dtype=x.dtype)
    for i in range(kh):
        for j in range(kw):
            cols[:, :, i, j] = xp[:, :, i:i + stride * OH:stride, j:j + stride * OW:stride]
    return cols.transpose(0, 4, 5, 1, 2, 3).reshape(N * OH * OW, C * kh * kw)


def col2im(cols: np.ndarray, x_shape: tuple[int, int, int, int], kh: int, kw: int,
           stride: int = 1, padding: int = 0) -> np.ndarray:
    """Phép ngược "theo kiểu adjoint" của im2col: cols (N*OH*OW, C*kh*kw) → mảng shape x_shape.

    Một pixel nằm trong nhiều cửa sổ thì CỘNG mọi giá trị tương ứng (đó là lý do gradient theo x đúng).
    Phần padding bị cắt bỏ.
    """
    N, C, H, W = x_shape
    OH, OW = output_size(H, kh, stride, padding), output_size(W, kw, stride, padding)
    c = cols.reshape(N, OH, OW, C, kh, kw).transpose(0, 3, 4, 5, 1, 2)
    xp = np.zeros((N, C, H + 2 * padding, W + 2 * padding), dtype=cols.dtype)
    for i in range(kh):
        for j in range(kw):
            xp[:, :, i:i + stride * OH:stride, j:j + stride * OW:stride] += c[:, :, i, j]
    return xp[:, :, padding:padding + H, padding:padding + W]


def conv2d_forward(x: np.ndarray, W: np.ndarray, b: np.ndarray, stride: int = 1,
                   padding: int = 0) -> tuple[np.ndarray, tuple]:
    """Trả (out, cache). out shape (N, F, OH, OW); cache chứa những gì backward cần."""
    N, C, H, Wd = x.shape
    F, _, kh, kw = W.shape
    OH, OW = output_size(H, kh, stride, padding), output_size(Wd, kw, stride, padding)
    cols = im2col(x, kh, kw, stride, padding)
    out = cols @ W.reshape(F, -1).T + b
    out = out.reshape(N, OH, OW, F).transpose(0, 3, 1, 2)
    return out, (x.shape, cols, W, stride, padding)


def conv2d_backward(dout: np.ndarray, cache: tuple) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """dout = dL/dout shape (N, F, OH, OW). Trả (dx, dW, db) cùng shape với x, W, b."""
    x_shape, cols, W, stride, padding = cache
    F, _, kh, kw = W.shape
    d = dout.transpose(0, 2, 3, 1).reshape(-1, F)
    dW = (d.T @ cols).reshape(W.shape)
    db = dout.sum(axis=(0, 2, 3))
    dx = col2im(d @ W.reshape(F, -1), x_shape, kh, kw, stride, padding)
    return dx, dW, db
