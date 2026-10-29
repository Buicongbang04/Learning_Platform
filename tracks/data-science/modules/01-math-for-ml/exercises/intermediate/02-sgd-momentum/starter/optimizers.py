"""Gradient descent, momentum và SGD minibatch, viết bằng numpy.

Quy ước: hàm trả "path" là mảng (n_iter + 1, d), hàng t là w sau t bước (hàng 0 là w0).
"""

from __future__ import annotations

from typing import Callable

import numpy as np

Grad = Callable[[np.ndarray], np.ndarray]


def quadratic_grad(A: np.ndarray, b: np.ndarray) -> Grad:
    """Gradient của f(w) = ½ wᵀAw − bᵀw (A đối xứng xác định dương): ∇f = Aw − b."""
    # TODO: trả một hàm (closure) nhận w
    raise NotImplementedError


def gd(grad: Grad, w0: np.ndarray, lr: float, n_iter: int) -> np.ndarray:
    """Gradient descent lr cố định. Trả path (n_iter + 1, d)."""
    # TODO
    raise NotImplementedError


def momentum(grad: Grad, w0: np.ndarray, lr: float, beta: float, n_iter: int) -> np.ndarray:
    """Heavy-ball momentum: v ← β v − lr ∇f(w); w ← w + v; v khởi tạo 0. Trả path."""
    # TODO
    raise NotImplementedError


def optimal_momentum_params(mu: float, L: float) -> tuple[float, float]:
    """lr và β tối ưu của heavy-ball cho hàm bậc hai có trị riêng trong [mu, L].

    lr = 4 / (√L + √mu)², β = ((√L − √mu) / (√L + √mu))².
    """
    # TODO
    raise NotImplementedError


def iterations_to_tol(path: np.ndarray, w_star: np.ndarray, tol: float = 1e-6) -> int:
    """Bước t đầu tiên có ‖w_t − w*‖ ≤ tol · ‖w_0 − w*‖; −1 nếu không bao giờ đạt."""
    # TODO
    raise NotImplementedError


def sgd_linreg(X: np.ndarray, y: np.ndarray, lr0: float, n_epochs: int, batch_size: int,
               seed: int = 0, decay: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Minibatch SGD cho MSE, w khởi tạo 0.

    Mỗi epoch xáo thứ tự bằng rng = np.random.default_rng(seed) (tạo một lần), chia thành các batch
    liên tiếp kích thước batch_size (batch cuối có thể nhỏ hơn). Bước cập nhật thứ t (đếm từ 0 trên
    toàn bộ quá trình) dùng lr = lr0 / (1 + decay · t), gradient MSE của batch: (2/m) X_bᵀ(X_b w − y_b).
    Trả (w, losses) với losses[e] là MSE trên toàn bộ dữ liệu sau epoch e (độ dài n_epochs).
    """
    # TODO: rng.permutation(n) mỗi epoch
    # TODO: cập nhật theo từng batch, đếm t để tính lr
    raise NotImplementedError
