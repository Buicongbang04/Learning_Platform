"""Huấn luyện DDP chịu được bị kill giữa chừng: checkpoint định kỳ, chạy lại thì tiếp từ checkpoint mới nhất đọc được.

Chạy (đủ cờ rendezvous: README module mục 0): torchrun --nproc_per_node=2 train_resumable.py --out /tmp/mlops-15/r1 --steps 120 --every 10
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import torch
import torch.distributed as dist
from torch import nn
from torch.nn.parallel import DistributedDataParallel as DDP

SEED = 11
N_SAMPLES = 4096
FEATURES = 16
BATCH_PER_RANK = 32
LR = 1e-3


def make_dataset(seed: int = SEED) -> tuple[torch.Tensor, torch.Tensor]:
    gen = torch.Generator().manual_seed(seed)
    x = torch.randn(N_SAMPLES, FEATURES, generator=gen)
    w = torch.randn(FEATURES, 1, generator=gen)
    return x, torch.sin(x @ w) + 0.05 * torch.randn(N_SAMPLES, 1, generator=gen)


def build_model(seed: int = SEED) -> nn.Module:
    torch.manual_seed(seed)
    return nn.Sequential(nn.Linear(FEATURES, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1))


def batch_indices(step: int, rank: int, world: int) -> torch.Tensor:
    """Batch của `rank` ở bước `step`: chỉ phụ thuộc (SEED, step, rank, world), không phụ thuộc trạng thái đã chạy."""
    global_batch = BATCH_PER_RANK * world
    per_epoch = N_SAMPLES // global_batch
    epoch, position = divmod(step, per_epoch)
    order = torch.randperm(N_SAMPLES, generator=torch.Generator().manual_seed(SEED * 1000 + epoch))
    chunk = order[position * global_batch:(position + 1) * global_batch]
    return chunk[rank::world]


def checkpoint_path(ckpt_dir: Path, step: int) -> Path:
    return ckpt_dir / f"step-{step:06d}.pt"


def save_checkpoint(ckpt_dir: Path, step: int, model: nn.Module, optimizer: torch.optim.Optimizer, rank: int) -> None:
    if rank == 0:
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        final = checkpoint_path(ckpt_dir, step)
        tmp = final.with_name(f".{final.name}.tmp")
        torch.save({"step": step, "model": model.state_dict(), "optimizer": optimizer.state_dict()}, tmp)
        with open(tmp, "rb") as handle:
            os.fsync(handle.fileno())
        os.replace(tmp, final)
    dist.barrier()


def load_latest(ckpt_dir: Path, model: nn.Module, optimizer: torch.optim.Optimizer) -> int:
    candidates = sorted(ckpt_dir.glob("step-*.pt"), reverse=True) if ckpt_dir.is_dir() else []
    for path in candidates:
        try:
            state = torch.load(path, weights_only=True)
            model.load_state_dict(state["model"])
            optimizer.load_state_dict(state["optimizer"])
            return int(state["step"])
        except Exception as error:
            print(f"bỏ qua checkpoint hỏng {path.name}: {type(error).__name__}", file=sys.stderr, flush=True)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--every", type=int, default=10)
    parser.add_argument("--step-delay", type=float, default=0.0)
    args = parser.parse_args()
    torch.set_num_threads(1)

    dist.init_process_group("gloo")
    rank, world = dist.get_rank(), dist.get_world_size()
    ckpt_dir = args.out / "ckpt"
    args.out.mkdir(parents=True, exist_ok=True)

    x, y = make_dataset()
    model = build_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    start = load_latest(ckpt_dir, model, optimizer)
    ddp = DDP(model)
    loss_fn = nn.MSELoss()

    log = open(args.out / "log.jsonl", "a") if rank == 0 else None
    if log:
        log.write(json.dumps({"event": "start", "from_step": start}) + "\n")
        log.flush()
    for step in range(start, args.steps):
        idx = batch_indices(step, rank, world)
        loss = loss_fn(ddp(x[idx]), y[idx])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if log:
            log.write(json.dumps({"step": step, "loss": loss.item()}) + "\n")
            log.flush()
        if (step + 1) % args.every == 0:
            save_checkpoint(ckpt_dir, step + 1, model, optimizer, rank)
        time.sleep(args.step_delay)

    if rank == 0:
        tmp = args.out / ".final.pt.tmp"
        torch.save(model.state_dict(), tmp)
        os.replace(tmp, args.out / "final.pt")
        log.close()
    dist.barrier()
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
