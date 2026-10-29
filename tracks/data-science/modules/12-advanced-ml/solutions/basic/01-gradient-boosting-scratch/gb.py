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
    """
    if loss not in LOSSES:
        raise ValueError(f"loss phải là một trong {LOSSES}")
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    init = float(np.mean(y)) if loss == "squared" else float(np.median(y))
    F = np.full(len(y), init)
    trees = []
    for _ in range(n_estimators):
        residual = y - F
        target = residual if loss == "squared" else np.sign(residual)
        tree = DecisionTreeRegressor(max_depth=max_depth, random_state=0).fit(X, target)
        if loss == "absolute":
            leaves = tree.apply(X)
            for leaf in np.unique(leaves):
                tree.tree_.value[leaf, 0, 0] = np.median(residual[leaves == leaf])
        F += learning_rate * tree.predict(X)
        trees.append(tree)
    return {"init": init, "trees": trees, "learning_rate": learning_rate, "loss": loss}


def predict_gb(model: dict, X, n_trees: int | None = None) -> np.ndarray:
    """Dự đoán bằng `n_trees` cây đầu tiên (None = tất cả). n_trees=0 trả về hằng số F0."""
    X = np.asarray(X, dtype=float)
    trees = model["trees"] if n_trees is None else model["trees"][:n_trees]
    pred = np.full(len(X), model["init"])
    for tree in trees:
        pred += model["learning_rate"] * tree.predict(X)
    return pred


def staged_loss(model: dict, X, y) -> np.ndarray:
    """Loss trên (X, y) sau 0, 1, …, M cây: MSE nếu loss="squared", MAE nếu loss="absolute"."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    pred = np.full(len(X), model["init"])
    metric = (lambda r: np.mean(r ** 2)) if model["loss"] == "squared" else (lambda r: np.mean(np.abs(r)))
    out = [metric(y - pred)]
    for tree in model["trees"]:
        pred = pred + model["learning_rate"] * tree.predict(X)
        out.append(metric(y - pred))
    return np.array(out)
