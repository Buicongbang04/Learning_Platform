"""Đo tham số, gradient và optimizer state mà mỗi rank giữ khi huấn luyện bằng DDP và bằng FSDP (CPU, gloo).

Chạy (đủ cờ rendezvous: README module mục 0): torchrun --nproc_per_node=2 shard_report.py --out /tmp/mlops-15/shard
"""

import argparse
import json
from pathlib import Path

import torch
import torch.distributed as dist
from torch import nn
from torch.distributed.fsdp import fully_shard
from torch.distributed.tensor import DTensor
from torch.nn.parallel import DistributedDataParallel as DDP

SEED = 5
FEATURES = 64
HIDDEN = 256
BATCH_PER_RANK = 32
LR = 1e-3
STEPS = 5
STRATEGIES = ("ddp", "fsdp")


def build_model(seed: int = SEED) -> nn.Module:
    torch.manual_seed(seed)
    return nn.Sequential(
        nn.Linear(FEATURES, HIDDEN), nn.ReLU(),
        nn.Linear(HIDDEN, HIDDEN), nn.ReLU(),
        nn.Linear(HIDDEN, HIDDEN), nn.ReLU(),
        nn.Linear(HIDDEN, 1),
    )


def rank_batch(step: int, rank: int) -> tuple[torch.Tensor, torch.Tensor]:
    gen = torch.Generator().manual_seed(SEED * 10_000 + step * 100 + rank)
    x = torch.randn(BATCH_PER_RANK, FEATURES, generator=gen)
    return x, torch.tanh(x[:, :8].sum(dim=1, keepdim=True))


def wrap(model: nn.Module, strategy: str) -> nn.Module:
    if strategy == "ddp":
        return DDP(model)
    if strategy == "fsdp":
        for layer in model:
            if isinstance(layer, nn.Linear):
                fully_shard(layer)
        fully_shard(model)
        return model
    raise ValueError(strategy)


def local_numel(tensors) -> int:
    total = 0
    for tensor in tensors:
        if tensor is None:
            continue
        total += tensor.to_local().numel() if isinstance(tensor, DTensor) else tensor.numel()
    return total


def optimizer_tensors(optimizer: torch.optim.Optimizer) -> list[torch.Tensor]:
    return [value for state in optimizer.state.values() for value in state.values()
            if isinstance(value, torch.Tensor) and value.dim() >= 1]


def train(strategy: str, rank: int, steps: int = STEPS) -> dict:
    model = wrap(build_model(), strategy)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    losses = []
    for step in range(steps):
        x, y = rank_batch(step, rank)
        loss = nn.functional.mse_loss(model(x), y)
        optimizer.zero_grad(set_to_none=False)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())
    params = list(model.parameters())
    return {
        "strategy": strategy,
        "rank": rank,
        "losses": losses,
        "param_numel": local_numel(params),
        "grad_numel": local_numel(p.grad for p in params),
        "optimizer_numel": local_numel(optimizer_tensors(optimizer)),
        "param_types": sorted({type(p).__name__ for p in params}),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    dist.init_process_group("gloo")
    rank = dist.get_rank()
    args.out.mkdir(parents=True, exist_ok=True)
    for strategy in STRATEGIES:
        report = train(strategy, rank)
        report["model_state_bytes"] = 4 * (report["param_numel"] + report["grad_numel"] + report["optimizer_numel"])
        (args.out / f"{strategy}-rank{rank}.json").write_text(json.dumps(report))
        dist.barrier()
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
