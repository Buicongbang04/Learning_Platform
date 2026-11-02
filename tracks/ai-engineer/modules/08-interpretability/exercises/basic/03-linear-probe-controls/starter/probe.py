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
    # TODO
    raise NotImplementedError


def standardize(X_train: np.ndarray, X_test: np.ndarray, eps: float = 1e-6) -> tuple[np.ndarray, np.ndarray]:
    """Trừ mean, chia std theo từng cột, cả hai tính **chỉ** trên train."""
    # TODO
    raise NotImplementedError


def train_linear_probe(X: np.ndarray, y: np.ndarray, n_classes: int, weight_decay: float = 1e-3, steps: int = 200, seed: int = 0) -> torch.nn.Linear:
    """Hồi quy logistic đa lớp: trả `nn.Linear(d, n_classes)` đã train full batch tới hội tụ (tối đa `steps` vòng lặp
    của optimizer), loss = cross-entropy trung bình + weight_decay * ||W||^2 (không phạt bias).
    `torch.manual_seed(seed)` trước khi tạo lớp Linear."""
    # TODO
    raise NotImplementedError


def probe_accuracy(probe: torch.nn.Linear, X: np.ndarray, y: np.ndarray) -> float:
    """Tỉ lệ dự đoán (argmax logits) đúng, kiểu float Python."""
    # TODO
    raise NotImplementedError


def control_labels(token_ids: np.ndarray, labels: np.ndarray, seed: int) -> np.ndarray:
    """Control task (Hewitt & Liang 2019): mỗi **loại** token (token id) nhận một nhãn cố định, rút ngẫu nhiên theo phân
    phối nhãn thực nghiệm của `labels`. Loại token duy nhất sắp tăng, rút bằng `np.random.default_rng(seed).choice`."""
    # TODO
    raise NotImplementedError


def majority_baseline(y_train: np.ndarray, y_test: np.ndarray) -> float:
    """Accuracy trên test khi luôn đoán nhãn phổ biến nhất của train (hoà thì nhãn nhỏ nhất)."""
    # TODO
    raise NotImplementedError


def mean_difference_direction(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Hướng "diff-in-means" của nhãn nhị phân: mean(X[y == 1]) - mean(X[y == 0]), chuẩn hoá về độ dài 1."""
    # TODO
    raise NotImplementedError
