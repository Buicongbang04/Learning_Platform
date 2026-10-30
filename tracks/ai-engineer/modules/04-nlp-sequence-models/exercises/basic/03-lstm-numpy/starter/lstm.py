"""LSTM một tầng bằng numpy: forward theo thời gian và backward (BPTT), cùng quy ước với torch.nn.LSTM."""

import numpy as np


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Sigmoid ổn định số (không tràn với |x| lớn)."""
    # TODO
    raise NotImplementedError


class LSTM:
    """x shape (T, N, D) (thời gian trước, giống nn.LSTM mặc định). Cổng xếp theo thứ tự i, f, g, o.

    W_ih (4H, D), W_hh (4H, H), b_ih (4H,), b_hh (4H,), khởi tạo U(-1/sqrt(H), 1/sqrt(H)),
    lấy từ rng theo đúng thứ tự W_ih, W_hh, b_ih, b_hh.
    """

    def __init__(self, input_size: int, hidden_size: int, rng: np.random.Generator):
        # TODO
        raise NotImplementedError

    def forward(self, x: np.ndarray, h0: np.ndarray | None = None, c0: np.ndarray | None = None):
        """Trả (out, (h_T, c_T)); out shape (T, N, H) là h_t ở mọi bước. h0, c0 mặc định bằng 0."""
        # TODO: lưu cache mỗi bước cho backward
        raise NotImplementedError

    def backward(self, dout: np.ndarray, dh_T: np.ndarray | None = None, dc_T: np.ndarray | None = None):
        """BPTT. dout = dL/dout (T, N, H); dh_T, dc_T là gradient thêm vào h_T, c_T (mặc định 0).

        Trả dx (T, N, D). Gán (không cộng dồn qua các lần gọi) self.dW_ih, self.dW_hh, self.db_ih,
        self.db_hh, self.dh0, self.dc0.
        """
        # TODO: đi ngược t = T-1 .. 0, mang theo dh_next, dc_next
        raise NotImplementedError


def clip_grad_norm(grads: list[np.ndarray], max_norm: float) -> float:
    """Cắt gradient theo chuẩn L2 TOÀN CỤC (gộp mọi mảng), sửa tại chỗ. Trả chuẩn trước khi cắt."""
    # TODO: giống torch.nn.utils.clip_grad_norm_ (hệ số max_norm / (total + 1e-6) khi total > max_norm)
    raise NotImplementedError
