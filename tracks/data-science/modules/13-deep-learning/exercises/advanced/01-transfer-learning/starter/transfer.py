"""Công cụ transfer learning cho model nn.Sequential có tầng cuối là nn.Linear (head)."""

from __future__ import annotations

import torch
from torch import nn


def select_classes(X: torch.Tensor, y: torch.Tensor, classes: list[int]) -> tuple[torch.Tensor, torch.Tensor]:
    """Giữ các mẫu có nhãn thuộc `classes` (giữ thứ tự gốc), đổi nhãn thành vị trí trong `classes`."""
    # TODO
    raise NotImplementedError


def few_shot_indices(y: torch.Tensor, n_per_class: int, seed: int = 0) -> torch.Tensor:
    """Chỉ số của đúng n_per_class mẫu mỗi lớp, chọn ngẫu nhiên không lặp theo seed.

    ValueError nếu lớp nào có ít hơn n_per_class mẫu.
    """
    # TODO
    raise NotImplementedError


def replace_head(model: nn.Sequential, n_classes: int) -> nn.Sequential:
    """Thay tầng Linear cuối bằng Linear mới (cùng in_features, out = n_classes). Sửa tại chỗ, trả model."""
    # TODO
    raise NotImplementedError


def freeze_backbone(model: nn.Sequential) -> None:
    """requires_grad = False cho mọi tham số trừ tầng cuối (head)."""
    # TODO
    raise NotImplementedError


def make_optimizer(model: nn.Sequential, head_lr: float, backbone_lr: float,
                   weight_decay: float = 0.0) -> torch.optim.AdamW:
    """AdamW với hai param group: backbone (backbone_lr) và head (head_lr), cùng weight_decay.

    Chỉ đưa vào tham số còn requires_grad; nếu backbone đã đóng băng thì chỉ có group head.
    """
    # TODO
    raise NotImplementedError


def fine_tune(model: nn.Module, X: torch.Tensor, y: torch.Tensor, epochs: int,
              optimizer: torch.optim.Optimizer, batch_size: int = 64, seed: int = 0) -> list[float]:
    """Vòng train cross-entropy với optimizer cho trước; xáo bằng Generator(seed + epoch).

    Trả loss trung bình theo mẫu mỗi epoch.
    """
    # TODO
    raise NotImplementedError
