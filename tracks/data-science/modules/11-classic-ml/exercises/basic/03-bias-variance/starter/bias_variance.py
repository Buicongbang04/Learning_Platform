"""Đo bias và variance của một model bằng mô phỏng: nhiều tập train, cùng một tập điểm test."""

from __future__ import annotations

from typing import Callable

import numpy as np

FitPredict = Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]


def simulate_predictions(fit_predict: FitPredict, f: Callable[[np.ndarray], np.ndarray], x_test: np.ndarray,
                         n_train: int, noise_sd: float, n_rep: int, seed: int) -> np.ndarray:
    """Lặp n_rep lần: rút x_train ~ Uniform(0, 1) cỡ n_train, y_train = f(x_train) + N(0, noise_sd²),
    gọi fit_predict(x_train, y_train, x_test). Trả mảng (n_rep, len(x_test)).

    Dùng một np.random.default_rng(seed) cho cả lần chạy: cùng seed thì cùng kết quả.
    """
    # TODO
    raise NotImplementedError


def decompose(preds: np.ndarray, f_test: np.ndarray, noise_sd: float) -> dict[str, float]:
    """Phân rã sai số kỳ vọng, lấy trung bình trên các điểm test.

    bias2       trung bình theo x của (trung bình dự đoán qua các lần - f(x))²
    variance    trung bình theo x của phương sai dự đoán qua các lần (ddof=0)
    noise       noise_sd²
    expected_mse bias2 + variance + noise
    """
    # TODO
    raise NotImplementedError


def knn_fit_predict(k: int) -> FitPredict:
    """Trả một hàm fit_predict dùng kNN regression với k láng giềng (x một chiều)."""
    # TODO: sklearn.neighbors.KNeighborsRegressor cần X dạng (n, 1)
    raise NotImplementedError
