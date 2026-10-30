"""nn.Module từ bên trong: RMSNorm, GroupNorm tự viết, block residual pre-norm, weight tying.

Chạy test: uv run pytest tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/basic/02-modules-norm-residual -q
"""

from __future__ import annotations

import torch
from torch import nn


class RMSNorm(nn.Module):
    """RMSNorm trên chiều cuối: y = x / sqrt(mean(x^2) + eps) * weight, weight là Parameter khởi tạo 1.

    Tính ở độ chính xác ít nhất float32 (input bf16/fp16 thì nâng lên float32, float64 giữ nguyên),
    rồi trả về đúng dtype của input (input bf16 thì output bf16).
    Khớp torch.nn.RMSNorm(dim, eps=eps). Không gọi torch.nn.RMSNorm hay F.rms_norm.
    """

    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        # TODO
        raise NotImplementedError

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError


def group_norm(
    x: torch.Tensor,
    num_groups: int,
    weight: torch.Tensor | None = None,
    bias: torch.Tensor | None = None,
    eps: float = 1e-5,
) -> torch.Tensor:
    """GroupNorm cho input (N, C, *): chia C kênh thành num_groups nhóm, chuẩn hoá mỗi (mẫu, nhóm) bằng mean
    và phương sai LỆCH (chia số phần tử) của nhóm đó; rồi nhân weight (C,), cộng bias (C,) theo kênh nếu có.

    C không chia hết cho num_groups thì ValueError. Không gọi F.group_norm / nn.GroupNorm.
    """
    # TODO
    raise NotImplementedError


class Block(nn.Module):
    """Block residual pre-norm kiểu Transformer (phần MLP): x + fc2(GELU(fc1(RMSNorm(x)))).

    Thuộc tính đúng tên: norm (RMSNorm(dim)), fc1 (Linear dim -> 4*dim), act (nn.GELU()), fc2 (Linear 4*dim -> dim).
    zero_init=True: weight và bias của fc2 khởi tạo bằng 0, nên lúc khởi tạo block là phép đồng nhất.
    """

    def __init__(self, dim: int, zero_init: bool = True):
        super().__init__()
        # TODO
        raise NotImplementedError

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError


class TinyLM(nn.Module):
    """embed (nn.Embedding) -> blocks (n_layers Block, lưu sao cho PyTorch thấy) -> norm (RMSNorm) -> head.

    head là nn.Linear(dim, vocab_size, bias=False) DÙNG CHUNG trọng số với embed (weight tying).
    forward(idx: (B, T) long) trả logits (B, T, vocab_size).
    """

    def __init__(self, vocab_size: int, dim: int, n_layers: int, zero_init: bool = True):
        super().__init__()
        # TODO
        raise NotImplementedError

    def forward(self, idx: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError


def weight_decay_groups(model: nn.Module, weight_decay: float) -> list[dict]:
    """Hai param group cho optimizer: [{"params": [...], "weight_decay": weight_decay},
    {"params": [...], "weight_decay": 0.0}].

    Nhóm đầu: tham số có từ 2 chiều trở lên (weight của Linear, Conv, Embedding). Nhóm sau: còn lại (bias,
    weight của norm). Chỉ tham số requires_grad; mỗi tham số đúng một lần, kể cả khi dùng chung (tied).
    """
    # TODO
    raise NotImplementedError


def parameter_report(model: nn.Module) -> dict[str, int]:
    """{"total": số phần tử tham số, "trainable": số phần tử tham số requires_grad,
    "buffers": số phần tử buffer, "bytes": tổng byte của tham số và buffer}. Tham số dùng chung tính một lần."""
    # TODO
    raise NotImplementedError
