import math

import torch
from torch import nn


class LoRALinear(nn.Module):
    """nn.Linear đóng băng cộng nhánh hạng thấp (alpha / r) * B A, A khởi tạo Kaiming đều, B bằng 0."""

    def __init__(self, base: nn.Linear, r: int, alpha: float, dropout: float = 0.0):
        super().__init__()
        # TODO: lưu base, r, alpha, scaling; tạo dropout; tạo lora_A (r, in_features) và lora_B (out_features, r)
        # TODO: khởi tạo A, B; đóng băng tham số của base; merged = False
        raise NotImplementedError

    def delta_weight(self) -> torch.Tensor:
        # TODO: ma trận cộng thêm vào base.weight, shape (out_features, in_features)
        raise NotImplementedError

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO
        raise NotImplementedError

    @torch.no_grad()
    def merge(self) -> None:
        # TODO
        raise NotImplementedError

    @torch.no_grad()
    def unmerge(self) -> None:
        # TODO
        raise NotImplementedError


def inject_lora(model: nn.Module, target_modules: list[str], r: int, alpha: float,
                dropout: float = 0.0) -> list[str]:
    # TODO
    raise NotImplementedError


def count_parameters(model: nn.Module) -> tuple[int, int]:
    # TODO: (số tham số train được, tổng số tham số)
    raise NotImplementedError


def merge_and_unload(model: nn.Module) -> nn.Module:
    # TODO
    raise NotImplementedError
