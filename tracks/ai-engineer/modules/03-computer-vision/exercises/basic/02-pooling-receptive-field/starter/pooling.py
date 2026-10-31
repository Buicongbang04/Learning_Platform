"""Pooling bằng numpy và các phép tính kích thước: output size, receptive field.

Quy ước NCHW như bài Basic 01: x shape (N, C, H, W). Pooling không padding, áp riêng từng kênh.
Chỉ dùng numpy trong tệp này; được lặp Python qua (i, j) của cửa sổ, không lặp qua N, C, OH, OW.
"""

from __future__ import annotations

import numpy as np


def conv_output_size(n: int, k: int, stride: int = 1, padding: int = 0, dilation: int = 1) -> int:
    """Kích thước output theo một chiều của conv/pool (công thức của nn.Conv2d)."""
    # TODO: kernel giãn (dilation d) phủ d*(k-1)+1 pixel
    raise NotImplementedError


def receptive_field(layers: list[tuple[int, ...]]) -> tuple[int, int]:
    """Receptive field của MỘT điểm output sau chồng tầng `layers`, tính trên input.

    Mỗi phần tử là (kernel, stride) hoặc (kernel, stride, dilation). Padding không đổi receptive field.
    Trả (rf, jump): rf là số pixel input theo một chiều mà điểm output "nhìn thấy", jump là khoảng cách
    (tính bằng pixel input) giữa hai điểm output kề nhau.
    """
    # TODO: đi từ tầng đầu, mỗi tầng nở rf thêm (k_eff - 1) * jump của tầng trước, rồi nhân jump với stride
    raise NotImplementedError


def maxpool2d_forward(x: np.ndarray, k: int, stride: int) -> tuple[np.ndarray, tuple]:
    """Trả (out, cache). Trong mỗi cửa sổ k x k lấy max; nhiều vị trí bằng nhau thì vị trí đầu tiên
    theo thứ tự hàng rồi cột thắng (như PyTorch)."""
    # TODO: gom k*k lát cắt (mỗi lát một vị trí trong cửa sổ) thành một trục, lấy max và argmax trên trục đó
    raise NotImplementedError


def maxpool2d_backward(dout: np.ndarray, cache: tuple) -> np.ndarray:
    """dout shape (N, C, OH, OW) → dx shape (N, C, H, W). Gradient chỉ về vị trí max của mỗi cửa sổ;
    một pixel là max của nhiều cửa sổ chồng nhau thì CỘNG gradient."""
    # TODO
    raise NotImplementedError


def avgpool2d_forward(x: np.ndarray, k: int, stride: int) -> tuple[np.ndarray, tuple]:
    """Trả (out, cache): trung bình mỗi cửa sổ k x k."""
    # TODO
    raise NotImplementedError


def avgpool2d_backward(dout: np.ndarray, cache: tuple) -> np.ndarray:
    """dout shape (N, C, OH, OW) → dx shape (N, C, H, W)."""
    # TODO: mỗi pixel trong cửa sổ nhận 1/(k*k) gradient của cửa sổ đó, cộng dồn khi chồng nhau
    raise NotImplementedError
