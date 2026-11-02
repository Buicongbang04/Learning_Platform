import math

import torch
from torch import nn


class LoRALinear(nn.Module):
    """nn.Linear đóng băng cộng nhánh hạng thấp (alpha / r) * B A, A khởi tạo Kaiming đều, B bằng 0."""

    def __init__(self, base: nn.Linear, r: int, alpha: float, dropout: float = 0.0):
        super().__init__()
        if r <= 0:
            raise ValueError("r phải dương")
        self.base = base
        self.r = r
        self.alpha = alpha
        self.scaling = alpha / r
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()
        weight = base.weight
        self.lora_A = nn.Parameter(torch.empty(r, base.in_features, device=weight.device, dtype=torch.float32))
        self.lora_B = nn.Parameter(torch.zeros(base.out_features, r, device=weight.device, dtype=torch.float32))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        for p in self.base.parameters():
            p.requires_grad_(False)
        self.merged = False

    def delta_weight(self) -> torch.Tensor:
        return (self.lora_B @ self.lora_A) * self.scaling

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.base(x)
        if self.merged:
            return out
        h = self.dropout(x).to(self.lora_A.dtype)
        lora = (h @ self.lora_A.T @ self.lora_B.T) * self.scaling
        return out + lora.to(out.dtype)

    @torch.no_grad()
    def merge(self) -> None:
        if self.merged:
            return
        w = self.base.weight
        w.copy_((w.float() + self.delta_weight()).to(w.dtype))
        self.merged = True

    @torch.no_grad()
    def unmerge(self) -> None:
        if not self.merged:
            return
        w = self.base.weight
        w.copy_((w.float() - self.delta_weight()).to(w.dtype))
        self.merged = False


def inject_lora(model: nn.Module, target_modules: list[str], r: int, alpha: float,
                dropout: float = 0.0) -> list[str]:
    for p in model.parameters():
        p.requires_grad_(False)
    targets = [name for name, m in model.named_modules()
               if isinstance(m, nn.Linear) and name.rsplit(".", 1)[-1] in set(target_modules)]
    if not targets:
        raise ValueError(f"không có nn.Linear nào khớp {target_modules}")
    for name in targets:
        parent_name, _, child = name.rpartition(".")
        parent = model.get_submodule(parent_name) if parent_name else model
        setattr(parent, child, LoRALinear(getattr(parent, child), r, alpha, dropout))
    return sorted(targets)


def count_parameters(model: nn.Module) -> tuple[int, int]:
    params = list(model.parameters())
    return sum(p.numel() for p in params if p.requires_grad), sum(p.numel() for p in params)


def merge_and_unload(model: nn.Module) -> nn.Module:
    names = [name for name, m in model.named_modules() if isinstance(m, LoRALinear)]
    for name in names:
        module = model.get_submodule(name)
        module.merge()
        parent_name, _, child = name.rpartition(".")
        parent = model.get_submodule(parent_name) if parent_name else model
        setattr(parent, child, module.base)
    return model
