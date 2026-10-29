"""Đo bias và variance của một model bằng mô phỏng: nhiều tập train, cùng một tập điểm test."""

from __future__ import annotations

from typing import Callable

import numpy as np
from sklearn.neighbors import KNeighborsRegressor

FitPredict = Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]


def simulate_predictions(fit_predict: FitPredict, f: Callable[[np.ndarray], np.ndarray], x_test: np.ndarray,
                         n_train: int, noise_sd: float, n_rep: int, seed: int) -> np.ndarray:
    """Lặp n_rep lần: rút x_train ~ Uniform(0, 1) cỡ n_train, y_train = f(x_train) + N(0, noise_sd²),
    gọi fit_predict(x_train, y_train, x_test). Trả mảng (n_rep, len(x_test)).

    Dùng một np.random.default_rng(seed) cho cả lần chạy: cùng seed thì cùng kết quả.
    """
    rng = np.random.default_rng(seed)
    x_test = np.asarray(x_test, dtype=float)
    out = np.empty((n_rep, len(x_test)))
    for r in range(n_rep):
        x = rng.random(n_train)
        y = f(x) + rng.normal(0, noise_sd, n_train)
        out[r] = fit_predict(x, y, x_test)
    return out


def decompose(preds: np.ndarray, f_test: np.ndarray, noise_sd: float) -> dict[str, float]:
    """Phân rã sai số kỳ vọng, lấy trung bình trên các điểm test.

    bias2       trung bình theo x của (trung bình dự đoán qua các lần - f(x))²
    variance    trung bình theo x của phương sai dự đoán qua các lần (ddof=0)
    noise       noise_sd²
    expected_mse bias2 + variance + noise
    """
    preds = np.asarray(preds, dtype=float)
    bias2 = float(np.mean((preds.mean(axis=0) - np.asarray(f_test)) ** 2))
    variance = float(np.mean(preds.var(axis=0)))
    noise = float(noise_sd**2)
    return {"bias2": bias2, "variance": variance, "noise": noise, "expected_mse": bias2 + variance + noise}


def knn_fit_predict(k: int) -> FitPredict:
    """Trả một hàm fit_predict dùng kNN regression với k láng giềng (x một chiều)."""

    def fit_predict(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray) -> np.ndarray:
        model = KNeighborsRegressor(n_neighbors=k).fit(np.reshape(x_train, (-1, 1)), y_train)
        return model.predict(np.reshape(x_test, (-1, 1)))

    return fit_predict
