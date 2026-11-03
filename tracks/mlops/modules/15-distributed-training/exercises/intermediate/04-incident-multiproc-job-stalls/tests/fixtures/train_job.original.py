"""Job huấn luyện ETA bản nhỏ chạy bằng torchrun.

Chạy (đủ cờ rendezvous: README module mục 0): torchrun --nproc_per_node=2 train_job.py --out /tmp/mlops-15/job --steps 40
"""

import argparse
import json
from pathlib import Path

import torch
import torch.distributed as dist
from torch import nn
from torch.nn.parallel import DistributedDataParallel as DDP

SEED = 21
FEATURES = 12
BATCH_PER_RANK = 32
LR = 0.02
LOG_EVERY = 10


def build_model(seed: int = SEED) -> nn.Module:
    torch.manual_seed(seed)
    return nn.Sequential(nn.Linear(FEATURES, 48), nn.ReLU(), nn.Linear(48, 1))


def rank_batch(step: int, rank: int) -> tuple[torch.Tensor, torch.Tensor]:
    gen = torch.Generator().manual_seed(SEED * 100_000 + step * 100 + rank)
    x = torch.randn(BATCH_PER_RANK, FEATURES, generator=gen)
    return x, torch.relu(x[:, :4].sum(dim=1, keepdim=True)) + 0.1 * x[:, 4:5]


def mean_over_workers(value: torch.Tensor) -> float:
    total = value.detach().clone()
    dist.all_reduce(total, op=dist.ReduceOp.SUM)
    return total.item() / dist.get_world_size()


class MetricsWriter:
    def __init__(self, out: Path, rank: int):
        self.rank = rank
        self.path = out / "metrics.jsonl"

    def write(self, step: int, loss: torch.Tensor) -> None:
        if self.rank != 0 or step % LOG_EVERY:
            return
        record = {"step": step, "loss": mean_over_workers(loss)}
        with open(self.path, "a") as handle:
            handle.write(json.dumps(record) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=40)
    args = parser.parse_args()
    torch.set_num_threads(1)

    dist.init_process_group("gloo")
    rank = dist.get_rank()
    args.out.mkdir(parents=True, exist_ok=True)

    model = DDP(build_model())
    optimizer = torch.optim.SGD(model.parameters(), lr=LR)
    metrics = MetricsWriter(args.out, rank)

    with open(args.out / f"rank{rank}.jsonl", "w") as trace:
        for step in range(args.steps):
            x, y = rank_batch(step, rank)
            loss = nn.functional.mse_loss(model(x), y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            metrics.write(step, loss)
            trace.write(json.dumps({"step": step, "loss": loss.item()}) + "\n")
            trace.flush()

    if rank == 0:
        torch.save(model.module.state_dict(), args.out / "model.pt")
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
