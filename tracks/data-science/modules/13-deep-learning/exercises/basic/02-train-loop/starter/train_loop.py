"""Vòng train chuẩn của PyTorch: train một epoch, đánh giá, và fit có early stopping."""

from __future__ import annotations

import copy

import torch
from torch import nn
from torch.utils.data import DataLoader


def train_one_epoch(model: nn.Module, loader: DataLoader, loss_fn, optimizer: torch.optim.Optimizer) -> float:
    """Một lượt qua loader: với mỗi batch zero_grad → forward → loss → backward → step.

    Model phải ở chế độ train (dropout, batchnorm hoạt động). loss_fn trả trung bình trên batch.
    Trả về loss trung bình THEO MẪU của cả epoch (batch cuối có thể nhỏ hơn), dạng float.
    """
    # TODO
    raise NotImplementedError


def evaluate(model: nn.Module, loader: DataLoader, loss_fn) -> dict[str, float]:
    """{"loss": loss trung bình theo mẫu, "accuracy": tỉ lệ argmax(logits) == y}.

    Chế độ eval và không theo dõi gradient.
    """
    # TODO
    raise NotImplementedError


def fit(model: nn.Module, train_loader: DataLoader, val_loader: DataLoader, loss_fn,
        optimizer: torch.optim.Optimizer, max_epochs: int = 50, patience: int = 5) -> dict:
    """Train tối đa max_epochs epoch, early stopping theo val loss (của evaluate).

    - Epoch đánh số từ 0. Một epoch "cải thiện" khi val loss NHỎ HƠN HẲN giá trị tốt nhất trước đó.
    - Dừng ngay sau epoch thứ `patience` liên tiếp không cải thiện.
    - Trước khi trả về, nạp lại trọng số của epoch tốt nhất vào model.

    Trả về {"train_loss": [...], "val_loss": [...], "best_epoch": int}.
    """
    # TODO: lưu bản sao state_dict tốt nhất bằng copy.deepcopy (state_dict() trả tham chiếu)
    raise NotImplementedError
