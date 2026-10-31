"""Pooling bằng numpy và các phép tính kích thước: output size, receptive field.

Quy ước NCHW như bài Basic 01: x shape (N, C, H, W). Pooling không padding, áp riêng từng kênh.
Chỉ dùng numpy trong tệp này; được lặp Python qua (i, j) của cửa sổ, không lặp qua N, C, OH, OW.
"""

from __future__ import annotations

import numpy as np


def conv_output_size(n: int, k: int, stride: int = 1, padding: int = 0, dilation: int = 1) -> int:
    """Kích thước output theo một chiều của conv/pool (công thức của nn.Conv2d)."""
    return (n + 2 * padding - dilation * (k - 1) - 1) // stride + 1


def receptive_field(layers: list[tuple[int, ...]]) -> tuple[int, int]:
    """Receptive field của MỘT điểm output sau chồng tầng `layers`, tính trên input.

    Mỗi phần tử là (kernel, stride) hoặc (kernel, stride, dilation). Padding không đổi receptive field.
    Trả (rf, jump): rf là số pixel input theo một chiều mà điểm output "nhìn thấy", jump là khoảng cách
    (tính bằng pixel input) giữa hai điểm output kề nhau.
    """
    rf, jump = 1, 1
    for layer in layers:
        k, s = layer[0], layer[1]
        d = layer[2] if len(layer) > 2 else 1
        rf += d * (k - 1) * jump
        jump *= s
    return rf, jump


def maxpool2d_forward(x: np.ndarray, k: int, stride: int) -> tuple[np.ndarray, tuple]:
    """Trả (out, cache). Trong mỗi cửa sổ k x k lấy max; nhiều vị trí bằng nhau thì vị trí đầu tiên
    theo thứ tự hàng rồi cột thắng (như PyTorch)."""
    N, C, H, W = x.shape
    OH, OW = conv_output_size(H, k, stride), conv_output_size(W, k, stride)
    win = np.stack([x[:, :, i:i + stride * OH:stride, j:j + stride * OW:stride]
                    for i in range(k) for j in range(k)], axis=2)       # (N, C, k*k, OH, OW)
    arg = win.argmax(axis=2)                                             # argmax trả vị trí đầu tiên
    out = np.take_along_axis(win, arg[:, :, None], axis=2)[:, :, 0]
    return out, (x.shape, k, stride, arg)


def maxpool2d_backward(dout: np.ndarray, cache: tuple) -> np.ndarray:
    """dout shape (N, C, OH, OW) → dx shape (N, C, H, W). Gradient chỉ về vị trí max của mỗi cửa sổ;
    một pixel là max của nhiều cửa sổ chồng nhau thì CỘNG gradient."""
    x_shape, k, stride, arg = cache
    OH, OW = dout.shape[2:]
    dx = np.zeros(x_shape, dtype=dout.dtype)
    for i in range(k):
        for j in range(k):
            dx[:, :, i:i + stride * OH:stride, j:j + stride * OW:stride] += dout * (arg == i * k + j)
    return dx


def avgpool2d_forward(x: np.ndarray, k: int, stride: int) -> tuple[np.ndarray, tuple]:
    """Trả (out, cache): trung bình mỗi cửa sổ k x k."""
    N, C, H, W = x.shape
    OH, OW = conv_output_size(H, k, stride), conv_output_size(W, k, stride)
    out = sum(x[:, :, i:i + stride * OH:stride, j:j + stride * OW:stride] for i in range(k) for j in range(k))
    return out / (k * k), (x.shape, k, stride)


def avgpool2d_backward(dout: np.ndarray, cache: tuple) -> np.ndarray:
    """dout shape (N, C, OH, OW) → dx shape (N, C, H, W)."""
    x_shape, k, stride = cache
    OH, OW = dout.shape[2:]
    dx = np.zeros(x_shape, dtype=dout.dtype)
    for i in range(k):
        for j in range(k):
            dx[:, :, i:i + stride * OH:stride, j:j + stride * OW:stride] += dout / (k * k)
    return dx
