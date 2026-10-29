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
    model.train()
    total, n = 0.0, 0
    for xb, yb in loader:
        optimizer.zero_grad()
        loss = loss_fn(model(xb), yb)
        loss.backward()
        optimizer.step()
        total += loss.item() * len(yb)      # loss là trung bình batch → nhân lại cỡ batch
        n += len(yb)
    return total / n


def evaluate(model: nn.Module, loader: DataLoader, loss_fn) -> dict[str, float]:
    """{"loss": loss trung bình theo mẫu, "accuracy": tỉ lệ argmax(logits) == y}.

    Chế độ eval và không theo dõi gradient.
    """
    model.eval()
    total, correct, n = 0.0, 0, 0
    with torch.no_grad():
        for xb, yb in loader:
            logits = model(xb)
            total += loss_fn(logits, yb).item() * len(yb)
            correct += (logits.argmax(dim=1) == yb).sum().item()
            n += len(yb)
    return {"loss": total / n, "accuracy": correct / n}


def fit(model: nn.Module, train_loader: DataLoader, val_loader: DataLoader, loss_fn,
        optimizer: torch.optim.Optimizer, max_epochs: int = 50, patience: int = 5) -> dict:
    """Train tối đa max_epochs epoch, early stopping theo val loss (của evaluate).

    - Epoch đánh số từ 0. Một epoch "cải thiện" khi val loss NHỎ HƠN HẲN giá trị tốt nhất trước đó.
    - Dừng ngay sau epoch thứ `patience` liên tiếp không cải thiện.
    - Trước khi trả về, nạp lại trọng số của epoch tốt nhất vào model.

    Trả về {"train_loss": [...], "val_loss": [...], "best_epoch": int}.
    """
    history = {"train_loss": [], "val_loss": [], "best_epoch": -1}
    best_loss, best_state, since_best = float("inf"), None, 0
    for epoch in range(max_epochs):
        history["train_loss"].append(train_one_epoch(model, train_loader, loss_fn, optimizer))
        val_loss = evaluate(model, val_loader, loss_fn)["loss"]
        history["val_loss"].append(val_loss)
        if val_loss < best_loss:
            best_loss, since_best = val_loss, 0
            history["best_epoch"] = epoch
            best_state = copy.deepcopy(model.state_dict())
        else:
            since_best += 1
            if since_best >= patience:
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    return history
