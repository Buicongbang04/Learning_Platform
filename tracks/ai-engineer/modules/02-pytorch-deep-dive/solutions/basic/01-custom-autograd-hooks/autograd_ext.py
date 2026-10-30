"""Mở rộng autograd: custom autograd.Function và hook (lời giải mẫu)."""

from __future__ import annotations

import torch
from torch import nn
from torch.utils.hooks import RemovableHandle


class SiLUFunction(torch.autograd.Function):
    """SiLU(x) = x * sigmoid(x) với backward tự viết."""

    @staticmethod
    def forward(ctx, x: torch.Tensor) -> torch.Tensor:
        s = torch.sigmoid(x)
        ctx.save_for_backward(x, s)
        return x * s

    @staticmethod
    def backward(ctx, grad_out: torch.Tensor) -> torch.Tensor:
        x, s = ctx.saved_tensors
        return grad_out * s * (1 + x * (1 - s))


def silu(x: torch.Tensor) -> torch.Tensor:
    return SiLUFunction.apply(x)


class RoundSTE(torch.autograd.Function):
    """Làm tròn ở forward, gradient đi thẳng (straight-through) ở backward."""

    @staticmethod
    def forward(ctx, x: torch.Tensor) -> torch.Tensor:
        return torch.round(x)

    @staticmethod
    def backward(ctx, grad_out: torch.Tensor) -> torch.Tensor:
        return grad_out


class GradReverse(torch.autograd.Function):
    """Forward là phép đồng nhất, backward nhân gradient với -lambd."""

    @staticmethod
    def forward(ctx, x: torch.Tensor, lambd: float) -> torch.Tensor:
        ctx.lambd = lambd
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_out: torch.Tensor):
        return -ctx.lambd * grad_out, None


def grad_reverse(x: torch.Tensor, lambd: float = 1.0) -> torch.Tensor:
    return GradReverse.apply(x, lambd)


def record_activations(
    model: nn.Module, types: tuple[type, ...] = (nn.ReLU,)
) -> tuple[dict[str, dict[str, float]], list[RemovableHandle]]:
    stats: dict[str, dict[str, float]] = {}
    handles: list[RemovableHandle] = []
    for name, module in model.named_modules():
        if not isinstance(module, types):
            continue

        def hook(mod, inputs, output, name=name):
            out = output.detach().float()
            stats[name] = {
                "mean": out.mean().item(),
                "std": out.std().item(),
                "frac_zero": (out == 0).float().mean().item(),
            }

        handles.append(module.register_forward_hook(hook))
    return stats, handles


def track_grad_norms(model: nn.Module) -> tuple[dict[str, list[float]], list[RemovableHandle]]:
    norms: dict[str, list[float]] = {}
    handles: list[RemovableHandle] = []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        norms[name] = []

        def hook(param, name=name):
            norms[name].append(param.grad.norm().item())

        handles.append(p.register_post_accumulate_grad_hook(hook))
    return norms, handles
