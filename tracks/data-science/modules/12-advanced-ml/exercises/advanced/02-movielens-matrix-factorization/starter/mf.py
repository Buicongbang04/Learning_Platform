"""Matrix factorization có bias cho rating tường minh (explicit feedback).

Mô hình: r̂(u, i) = μ + b_u + b_i + p_u · q_i, với μ là trung bình rating của train.
Bạn chọn cách học (ALS hoặc SGD) và các giá trị mặc định của reg, n_iters cho phù hợp.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class MatrixFactorization:
    def __init__(self, n_factors: int = 20, reg: float = 10.0, n_iters: int = 15, seed: int = 0):
        # reg, n_iters: đổi mặc định nếu cách học của bạn cần thang khác (SGD thường dùng reg ~0.05)
        self.n_factors, self.reg, self.n_iters, self.seed = n_factors, reg, n_iters, seed

    def fit(self, ratings: pd.DataFrame) -> "MatrixFactorization":
        """Học μ, b_u, b_i, p_u, q_i từ DataFrame có cột userId, movieId, rating. Trả self.

        Khởi tạo ngẫu nhiên bằng np.random.default_rng(self.seed) để kết quả tái lập được.
        """
        # TODO: mã hoá userId, movieId thành chỉ số; μ = trung bình rating
        # TODO: lặp n_iters vòng ALS (giải least squares có regularization cho từng user rồi từng item)
        #       hoặc SGD (duyệt rating theo thứ tự ngẫu nhiên, cập nhật b_u, b_i, p_u, q_i)
        raise NotImplementedError

    def predict(self, users, items) -> np.ndarray:
        """Dự đoán rating cho từng cặp (users[j], items[j]).

        Cold start: user không có trong train thì b_u = 0 và p_u = 0; phim không có trong train thì
        b_i = 0 và q_i = 0. User lạ + phim lạ → μ.
        """
        # TODO
        raise NotImplementedError

    def recommend(self, user, k: int = 10, exclude=()) -> list:
        """k phim (trong số phim có ở train) có rating dự đoán cao nhất, bỏ các phim trong exclude."""
        # TODO
        raise NotImplementedError
