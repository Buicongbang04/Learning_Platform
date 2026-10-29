"""Gradient descent, momentum và SGD minibatch, viết bằng numpy.

Quy ước: hàm trả "path" là mảng (n_iter + 1, d), hàng t là w sau t bước (hàng 0 là w0).
"""

from __future__ import annotations

from typing import Callable

import numpy as np

Grad = Callable[[np.ndarray], np.ndarray]


def quadratic_grad(A: np.ndarray, b: np.ndarray) -> Grad:
    """Gradient của f(w) = ½ wᵀAw − bᵀw (A đối xứng xác định dương): ∇f = Aw − b."""
    return lambda w: A @ w - b


def gd(grad: Grad, w0: np.ndarray, lr: float, n_iter: int) -> np.ndarray:
    """Gradient descent lr cố định. Trả path (n_iter + 1, d)."""
    path = np.empty((n_iter + 1, len(w0)))
    path[0] = w = np.asarray(w0, dtype=float)
    for t in range(n_iter):
        w = w - lr * grad(w)
        path[t + 1] = w
    return path


def momentum(grad: Grad, w0: np.ndarray, lr: float, beta: float, n_iter: int) -> np.ndarray:
    """Heavy-ball momentum: v ← β v − lr ∇f(w); w ← w + v; v khởi tạo 0. Trả path."""
    path = np.empty((n_iter + 1, len(w0)))
    path[0] = w = np.asarray(w0, dtype=float)
    v = np.zeros_like(w)
    for t in range(n_iter):
        v = beta * v - lr * grad(w)
        w = w + v
        path[t + 1] = w
    return path


def optimal_momentum_params(mu: float, L: float) -> tuple[float, float]:
    """lr và β tối ưu của heavy-ball cho hàm bậc hai có trị riêng trong [mu, L]."""
    lr = 4 / (np.sqrt(L) + np.sqrt(mu)) ** 2
    beta = ((np.sqrt(L) - np.sqrt(mu)) / (np.sqrt(L) + np.sqrt(mu))) ** 2
    return float(lr), float(beta)


def iterations_to_tol(path: np.ndarray, w_star: np.ndarray, tol: float = 1e-6) -> int:
    """Bước t đầu tiên có ‖w_t − w*‖ ≤ tol · ‖w_0 − w*‖; −1 nếu không bao giờ đạt."""
    dist = np.linalg.norm(path - w_star, axis=1)
    hit = np.nonzero(dist <= tol * dist[0])[0]
    return int(hit[0]) if len(hit) else -1


def sgd_linreg(X: np.ndarray, y: np.ndarray, lr0: float, n_epochs: int, batch_size: int,
               seed: int = 0, decay: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Minibatch SGD cho MSE, w khởi tạo 0.

    Mỗi epoch xáo thứ tự bằng rng = np.random.default_rng(seed) (tạo một lần), chia thành các batch
    liên tiếp kích thước batch_size (batch cuối có thể nhỏ hơn). Bước cập nhật thứ t (đếm từ 0 trên
    toàn bộ quá trình) dùng lr = lr0 / (1 + decay · t), gradient MSE của batch: (2/m) X_bᵀ(X_b w − y_b).
    Trả (w, losses) với losses[e] là MSE trên toàn bộ dữ liệu sau epoch e (độ dài n_epochs).
    """
    rng = np.random.default_rng(seed)
    n = len(y)
    w = np.zeros(X.shape[1])
    losses = np.empty(n_epochs)
    t = 0
    for epoch in range(n_epochs):
        order = rng.permutation(n)
        for start in range(0, n, batch_size):
            idx = order[start:start + batch_size]
            Xb, yb = X[idx], y[idx]
            w = w - lr0 / (1 + decay * t) * (2 / len(idx)) * Xb.T @ (Xb @ w - yb)
            t += 1
        r = X @ w - y
        losses[epoch] = r @ r / n
    return w, losses
