import torch
import torch.nn.functional as F
from torch import nn

IGNORE_INDEX = -100


def sequence_logps(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    """Tổng log-xác suất của các token có label (khác -100) của mỗi chuỗi, shape (batch,)."""
    # TODO
    raise NotImplementedError


def dpo_loss(policy_chosen: torch.Tensor, policy_rejected: torch.Tensor, ref_chosen: torch.Tensor,
             ref_rejected: torch.Tensor, beta: float = 0.1) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    # TODO: (loss trung bình, reward ngầm của chosen, reward ngầm của rejected)
    raise NotImplementedError


def dpo_step(policy: nn.Module, reference: nn.Module, batch: dict[str, torch.Tensor], beta: float,
             optimizer: torch.optim.Optimizer) -> dict[str, float]:
    # TODO
    raise NotImplementedError
