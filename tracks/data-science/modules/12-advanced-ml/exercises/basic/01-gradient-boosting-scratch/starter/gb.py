"""Gradient boosting cho hồi quy, viết từ đầu, base learner là cây quyết định của sklearn."""

from __future__ import annotations

import numpy as np
from sklearn.tree import DecisionTreeRegressor

LOSSES = ("squared", "absolute")


def fit_gb(X, y, n_estimators: int = 100, learning_rate: float = 0.1, max_depth: int = 3,
           loss: str = "squared") -> dict:
    """Huấn luyện gradient boosting. Trả về dict: init, trees, learning_rate, loss.

    loss="squared": F0 = mean(y); mỗi vòng fit cây lên phần dư y − F (negative gradient).
    loss="absolute": F0 = median(y); mỗi vòng fit cây lên sign(y − F), rồi đặt lại giá trị mỗi lá
    bằng median của phần dư y − F của các điểm rơi vào lá đó (line search theo từng lá).
    Cây: DecisionTreeRegressor(max_depth=max_depth, random_state=0).
    loss không thuộc LOSSES → ValueError.
    """
    # TODO: kiểm tra loss, tính F0 và mảng F (dự đoán hiện tại trên tập train)
    # TODO: lặp n_estimators vòng: negative gradient → fit cây → (absolute) sửa giá trị lá
    #       → F += learning_rate * tree.predict(X)
    raise NotImplementedError


def predict_gb(model: dict, X, n_trees: int | None = None) -> np.ndarray:
    """Dự đoán bằng `n_trees` cây đầu tiên (None = tất cả). n_trees=0 trả về hằng số F0."""
    # TODO
    raise NotImplementedError


def staged_loss(model: dict, X, y) -> np.ndarray:
    """Loss trên (X, y) sau 0, 1, …, M cây (mảng dài M + 1).

    MSE nếu model["loss"] == "squared", MAE nếu "absolute".
    """
    # TODO: cộng dồn từng cây, không gọi predict_gb lại từ đầu M lần
    raise NotImplementedError
