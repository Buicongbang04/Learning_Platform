"""Mở rộng autograd: custom autograd.Function và hook.

Chạy test: uv run pytest tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/basic/01-custom-autograd-hooks -q
"""

from __future__ import annotations

import torch
from torch import nn
from torch.utils.hooks import RemovableHandle


class SiLUFunction(torch.autograd.Function):
    """SiLU(x) = x * sigmoid(x), backward TỰ VIẾT (không gọi F.silu, không để autograd tự suy).

    forward lưu những gì backward cần bằng ctx.save_for_backward; backward trả dL/dx.
    """

    @staticmethod
    def forward(ctx, x: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError

    @staticmethod
    def backward(ctx, grad_out: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError


def silu(x: torch.Tensor) -> torch.Tensor:
    """Gọi SiLUFunction (qua .apply, không gọi forward trực tiếp)."""
    # TODO
    raise NotImplementedError


class RoundSTE(torch.autograd.Function):
    """Forward: torch.round(x). Backward: straight-through estimator, gradient đi qua nguyên vẹn."""

    @staticmethod
    def forward(ctx, x: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError

    @staticmethod
    def backward(ctx, grad_out: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError


class GradReverse(torch.autograd.Function):
    """Gradient reversal layer: forward(x, lambd) trả x (giá trị không đổi), backward trả -lambd * grad.

    lambd là số Python, không phải tensor: backward phải trả gradient cho MỌI input của forward.
    """

    @staticmethod
    def forward(ctx, x: torch.Tensor, lambd: float) -> torch.Tensor:
        # TODO
        raise NotImplementedError

    @staticmethod
    def backward(ctx, grad_out: torch.Tensor):
        # TODO
        raise NotImplementedError


def grad_reverse(x: torch.Tensor, lambd: float = 1.0) -> torch.Tensor:
    # TODO
    raise NotImplementedError


def record_activations(
    model: nn.Module, types: tuple[type, ...] = (nn.ReLU,)
) -> tuple[dict[str, dict[str, float]], list[RemovableHandle]]:
    """Gắn forward hook vào mọi module con có kiểu thuộc `types`.

    Mỗi lần forward, ghi (ghi đè) stats[<tên module trong named_modules>] =
    {"mean": ..., "std": ..., "frac_zero": ...} tính trên OUTPUT của module đó, kiểu float Python
    (std theo mặc định của torch, chia N - 1; frac_zero là tỉ lệ phần tử bằng 0).
    Trả (stats, handles); gọi h.remove() cho mọi handle thì ngừng ghi.
    """
    # TODO
    raise NotImplementedError


def track_grad_norms(model: nn.Module) -> tuple[dict[str, list[float]], list[RemovableHandle]]:
    """Mỗi tham số requires_grad: sau MỖI lần gradient được cộng dồn vào .grad, thêm norm L2 của .grad
    (giá trị đã cộng dồn, float Python) vào norms[<tên tham số trong named_parameters>].

    Trả (norms, handles). Tham số đã đóng băng (requires_grad=False) không có trong norms.
    """
    # TODO
    raise NotImplementedError
