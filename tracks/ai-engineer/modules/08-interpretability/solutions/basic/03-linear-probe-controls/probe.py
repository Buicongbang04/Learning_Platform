"""Linear probe có đối chứng: chia theo nhóm, chuẩn hoá theo train, control task, baseline."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F


def group_split(groups: np.ndarray, test_frac: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Chia theo nhóm (ví dụ id câu): mọi mẫu của một nhóm nằm cùng một phía.

    Nhóm duy nhất sắp tăng (`np.unique`), hoán vị bằng `np.random.default_rng(seed).permutation`, `round(test_frac * n_nhóm)`
    nhóm đầu của hoán vị vào test. Trả hai mảng chỉ số mẫu (tăng dần).
    """
    groups = np.asarray(groups)
    uniq = np.unique(groups)
    perm = np.random.default_rng(seed).permutation(len(uniq))
    test_groups = uniq[perm[: int(round(test_frac * len(uniq)))]]
    is_test = np.isin(groups, test_groups)
    return np.flatnonzero(~is_test), np.flatnonzero(is_test)


def standardize(X_train: np.ndarray, X_test: np.ndarray, eps: float = 1e-6) -> tuple[np.ndarray, np.ndarray]:
    """Trừ mean, chia std theo từng cột, cả hai tính **chỉ** trên train."""
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0) + eps
    return (X_train - mean) / std, (X_test - mean) / std


def train_linear_probe(X: np.ndarray, y: np.ndarray, n_classes: int, weight_decay: float = 1e-3, steps: int = 200, seed: int = 0) -> torch.nn.Linear:
    """Hồi quy logistic đa lớp `nn.Linear(d, n_classes)`, full batch, L-BFGS, loss = cross-entropy trung bình
    + weight_decay * ||W||^2 (không phạt bias). `torch.manual_seed(seed)` trước khi tạo lớp Linear."""
    torch.manual_seed(seed)
    Xt = torch.as_tensor(X, dtype=torch.float32)
    yt = torch.as_tensor(y, dtype=torch.long)
    probe = torch.nn.Linear(Xt.shape[1], n_classes)
    opt = torch.optim.LBFGS(probe.parameters(), lr=1.0, max_iter=steps, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = F.cross_entropy(probe(Xt), yt) + weight_decay * probe.weight.pow(2).sum()
        loss.backward()
        return loss

    opt.step(closure)
    return probe


def probe_accuracy(probe: torch.nn.Linear, X: np.ndarray, y: np.ndarray) -> float:
    """Tỉ lệ dự đoán (argmax logits) đúng, kiểu float Python."""
    with torch.no_grad():
        pred = probe(torch.as_tensor(X, dtype=torch.float32)).argmax(dim=-1).numpy()
    return float((pred == np.asarray(y)).mean())


def control_labels(token_ids: np.ndarray, labels: np.ndarray, seed: int) -> np.ndarray:
    """Control task (Hewitt & Liang 2019): mỗi **loại** token (token id) nhận một nhãn cố định, rút ngẫu nhiên theo phân
    phối nhãn thực nghiệm của `labels`. Loại token duy nhất sắp tăng, rút bằng `np.random.default_rng(seed).choice`."""
    token_ids, labels = np.asarray(token_ids), np.asarray(labels)
    values, counts = np.unique(labels, return_counts=True)
    types, inverse = np.unique(token_ids, return_inverse=True)
    per_type = np.random.default_rng(seed).choice(values, size=len(types), p=counts / counts.sum())
    return per_type[inverse]


def majority_baseline(y_train: np.ndarray, y_test: np.ndarray) -> float:
    """Accuracy trên test khi luôn đoán nhãn phổ biến nhất của train (hoà thì nhãn nhỏ nhất)."""
    values, counts = np.unique(y_train, return_counts=True)
    return float((np.asarray(y_test) == values[counts.argmax()]).mean())


def mean_difference_direction(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Hướng "diff-in-means" của nhãn nhị phân: mean(X[y == 1]) - mean(X[y == 0]), chuẩn hoá về độ dài 1."""
    d = X[y == 1].mean(axis=0) - X[y == 0].mean(axis=0)
    return d / np.linalg.norm(d)
