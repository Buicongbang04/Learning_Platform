"""LSTM một tầng bằng numpy: forward theo thời gian và backward (BPTT), cùng quy ước với torch.nn.LSTM."""

import numpy as np


def sigmoid(x: np.ndarray) -> np.ndarray:
    out = np.empty_like(x)
    pos = x >= 0
    out[pos] = 1 / (1 + np.exp(-x[pos]))
    e = np.exp(x[~pos])
    out[~pos] = e / (1 + e)
    return out


class LSTM:
    """x shape (T, N, D) (thời gian trước, giống nn.LSTM mặc định). Cổng xếp theo thứ tự i, f, g, o.

    W_ih (4H, D), W_hh (4H, H), b_ih (4H,), b_hh (4H,), khởi tạo U(-1/sqrt(H), 1/sqrt(H)),
    lấy từ rng theo đúng thứ tự W_ih, W_hh, b_ih, b_hh.
    """

    def __init__(self, input_size: int, hidden_size: int, rng: np.random.Generator):
        H, D = hidden_size, input_size
        k = 1 / np.sqrt(H)
        self.H = H
        self.W_ih = rng.uniform(-k, k, (4 * H, D))
        self.W_hh = rng.uniform(-k, k, (4 * H, H))
        self.b_ih = rng.uniform(-k, k, 4 * H)
        self.b_hh = rng.uniform(-k, k, 4 * H)

    def forward(self, x: np.ndarray, h0: np.ndarray | None = None, c0: np.ndarray | None = None):
        """Trả (out, (h_T, c_T)); out shape (T, N, H) là h_t ở mọi bước. h0, c0 mặc định bằng 0."""
        T, N, _ = x.shape
        H = self.H
        h = np.zeros((N, H)) if h0 is None else h0
        c = np.zeros((N, H)) if c0 is None else c0
        self.cache = []
        out = np.empty((T, N, H))
        for t in range(T):
            z = x[t] @ self.W_ih.T + h @ self.W_hh.T + self.b_ih + self.b_hh
            i, f, o = sigmoid(z[:, :H]), sigmoid(z[:, H:2 * H]), sigmoid(z[:, 3 * H:])
            g = np.tanh(z[:, 2 * H:3 * H])
            c_new = f * c + i * g
            tc = np.tanh(c_new)
            h_new = o * tc
            self.cache.append((x[t], h, c, i, f, g, o, tc))
            h, c = h_new, c_new
            out[t] = h
        return out, (h, c)

    def backward(self, dout: np.ndarray, dh_T: np.ndarray | None = None, dc_T: np.ndarray | None = None):
        """BPTT. dout = dL/dout (T, N, H); dh_T, dc_T là gradient thêm vào h_T, c_T (mặc định 0).

        Trả dx (T, N, D). Gán (không cộng dồn qua các lần gọi) self.dW_ih, self.dW_hh, self.db_ih,
        self.db_hh, self.dh0, self.dc0.
        """
        T, N, H = dout.shape
        dW_ih, dW_hh = np.zeros_like(self.W_ih), np.zeros_like(self.W_hh)
        db = np.zeros(4 * H)
        dx = np.empty((T, N, self.W_ih.shape[1]))
        dh_next = np.zeros((N, H)) if dh_T is None else dh_T.copy()
        dc_next = np.zeros((N, H)) if dc_T is None else dc_T.copy()
        for t in reversed(range(T)):
            xt, h_prev, c_prev, i, f, g, o, tc = self.cache[t]
            dh = dout[t] + dh_next
            dc = dc_next + dh * o * (1 - tc ** 2)
            dz = np.concatenate([
                dc * g * i * (1 - i),          # cổng i
                dc * c_prev * f * (1 - f),     # cổng f
                dc * i * (1 - g ** 2),         # g
                dh * tc * o * (1 - o),         # cổng o
            ], axis=1)
            dW_ih += dz.T @ xt
            dW_hh += dz.T @ h_prev
            db += dz.sum(axis=0)
            dx[t] = dz @ self.W_ih
            dh_next = dz @ self.W_hh
            dc_next = dc * f
        self.dW_ih, self.dW_hh, self.db_ih, self.db_hh = dW_ih, dW_hh, db, db.copy()
        self.dh0, self.dc0 = dh_next, dc_next
        return dx


def clip_grad_norm(grads: list[np.ndarray], max_norm: float) -> float:
    """Cắt gradient theo chuẩn L2 TOÀN CỤC (gộp mọi mảng), sửa tại chỗ. Trả chuẩn trước khi cắt."""
    total = float(np.sqrt(sum(float(np.sum(g * g)) for g in grads)))
    if total > max_norm:
        scale = max_norm / (total + 1e-6)
        for g in grads:
            g *= scale
    return total
