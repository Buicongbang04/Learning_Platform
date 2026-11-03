"""Huấn luyện MLP nhỏ bằng DDP trên CPU (backend gloo).

Chạy (đủ cờ rendezvous: README module mục 0): torchrun --nproc_per_node=2 train_ddp.py --out /tmp/mlops-15/ddp --steps 60
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

import torch
import torch.distributed as dist
from torch import nn
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler, TensorDataset

SEED = 7
N_SAMPLES = 2048
FEATURES = 16
BATCH_PER_RANK = 32
LR = 0.05


def make_dataset(seed: int = SEED) -> TensorDataset:
    gen = torch.Generator().manual_seed(seed)
    x = torch.randn(N_SAMPLES, FEATURES, generator=gen)
    w = torch.randn(FEATURES, 1, generator=gen)
    y = torch.tanh(x @ w) + 0.05 * torch.randn(N_SAMPLES, 1, generator=gen)
    return TensorDataset(x, y, torch.arange(N_SAMPLES))


def build_model(seed: int = SEED) -> nn.Module:
    torch.manual_seed(seed)
    return nn.Sequential(nn.Linear(FEATURES, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1))


def param_digest(model: nn.Module) -> str:
    digest = hashlib.sha256()
    for param in model.parameters():
        digest.update(param.detach().contiguous().numpy().tobytes())
    return digest.hexdigest()[:16]


def setup() -> tuple[int, int, int]:
    dist.init_process_group(backend="gloo")
    return dist.get_rank(), dist.get_world_size(), int(os.environ["LOCAL_RANK"])


def make_loader(dataset: TensorDataset, rank: int, world: int) -> tuple[DataLoader, DistributedSampler]:
    sampler = DistributedSampler(dataset, num_replicas=world, rank=rank, shuffle=True, seed=SEED, drop_last=True)
    return DataLoader(dataset, batch_size=BATCH_PER_RANK, sampler=sampler, drop_last=True), sampler


def wrap(model: nn.Module) -> nn.Module:
    return DDP(model)


def start_epoch(sampler: DistributedSampler, epoch: int) -> None:
    sampler.set_epoch(epoch)


def teardown() -> None:
    dist.destroy_process_group()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=60)
    args = parser.parse_args()
    torch.set_num_threads(1)

    rank, world, local_rank = setup()
    args.out.mkdir(parents=True, exist_ok=True)
    meta = {"rank": rank, "local_rank": local_rank, "world_size": world, "backend": dist.get_backend()}
    (args.out / f"rank{rank}-meta.json").write_text(json.dumps(meta))

    dataset = make_dataset()
    loader, sampler = make_loader(dataset, rank, world)
    model = wrap(build_model())
    optimizer = torch.optim.SGD(model.parameters(), lr=LR)
    loss_fn = nn.MSELoss()

    step, epoch = 0, 0
    with open(args.out / f"rank{rank}.jsonl", "w") as log:
        while step < args.steps:
            start_epoch(sampler, epoch)
            for x, y, idx in loader:
                loss = loss_fn(model(x), y)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                record = {"step": step, "epoch": epoch, "loss": loss.item(), "digest": param_digest(model),
                          "indices": idx.tolist()}
                log.write(json.dumps(record) + "\n")
                step += 1
                if step >= args.steps:
                    break
            epoch += 1

    plain = model.module if isinstance(model, DDP) else model
    torch.save(plain.state_dict(), args.out / f"rank{rank}-final.pt")
    teardown()


if __name__ == "__main__":
    main()
