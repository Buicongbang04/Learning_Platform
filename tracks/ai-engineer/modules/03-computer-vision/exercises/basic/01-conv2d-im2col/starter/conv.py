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
    # TODO: pad x bằng 0, lấy từng lát cắt có bước nhảy stride cho mỗi (i, j) của kernel, rồi sắp lại trục
    raise NotImplementedError


def col2im(cols: np.ndarray, x_shape: tuple[int, int, int, int], kh: int, kw: int,
           stride: int = 1, padding: int = 0) -> np.ndarray:
    """Phép ngược "theo kiểu adjoint" của im2col: cols (N*OH*OW, C*kh*kw) → mảng shape x_shape.

    Một pixel nằm trong nhiều cửa sổ thì CỘNG mọi giá trị tương ứng (đó là lý do gradient theo x đúng).
    Phần padding bị cắt bỏ.
    """
    # TODO
    raise NotImplementedError


def conv2d_forward(x: np.ndarray, W: np.ndarray, b: np.ndarray, stride: int = 1,
                   padding: int = 0) -> tuple[np.ndarray, tuple]:
    """Trả (out, cache). out shape (N, F, OH, OW); cache chứa những gì backward cần."""
    # TODO: im2col rồi một phép nhân ma trận với W.reshape(F, -1), cộng b, sắp lại về NCHW
    raise NotImplementedError


def conv2d_backward(dout: np.ndarray, cache: tuple) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """dout = dL/dout shape (N, F, OH, OW). Trả (dx, dW, db) cùng shape với x, W, b."""
    # TODO: dW và db từ cols; dx đi qua col2im
    raise NotImplementedError
