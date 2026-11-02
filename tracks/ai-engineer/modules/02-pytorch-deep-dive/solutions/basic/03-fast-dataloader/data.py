"""Pipeline dữ liệu CIFAR-10: decode một lần, Dataset có augmentation, worker có seed, augmentation theo batch (lời giải mẫu)."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import torch
import torch.nn.functional as F
from PIL import Image
from torch.utils.data import DataLoader, Dataset, get_worker_info

CIFAR_MEAN = (0.4914, 0.4822, 0.4465)
CIFAR_STD = (0.2470, 0.2435, 0.2616)


def decode_cifar_parquet(path: str | Path) -> tuple[torch.Tensor, torch.Tensor]:
    table = pq.read_table(path, columns=["img", "label"])
    images = [np.asarray(Image.open(io.BytesIO(d["bytes"])).convert("RGB")) for d in table.column("img").to_pylist()]
    x = torch.from_numpy(np.stack(images)).permute(0, 3, 1, 2).contiguous()
    y = torch.from_numpy(table.column("label").to_numpy().astype(np.int64))
    return x, y


class CifarDataset(Dataset):
    def __init__(self, images: torch.Tensor, labels: torch.Tensor, augment: bool = False, seed: int = 0):
        self.images, self.labels, self.augment = images, labels, augment
        self.mean = torch.tensor(CIFAR_MEAN).view(3, 1, 1)
        self.std = torch.tensor(CIFAR_STD).view(3, 1, 1)
        self.rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        x = self.images[i]
        if self.augment:
            padded = F.pad(x.unsqueeze(0).float(), (4, 4, 4, 4), mode="reflect")[0]
            dy, dx = self.rng.integers(0, 9, size=2)
            x = padded[:, dy:dy + 32, dx:dx + 32]
            if self.rng.random() < 0.5:
                x = x.flip(2)
        x = (x.float() / 255 - self.mean) / self.std
        return x, int(self.labels[i])


def seed_worker(worker_id: int) -> None:
    info = get_worker_info()
    if info is not None and hasattr(info.dataset, "rng"):
        info.dataset.rng = np.random.default_rng(torch.initial_seed() % 2**32)


def make_loader(dataset: Dataset, batch_size: int, shuffle: bool, num_workers: int, seed: int) -> DataLoader:
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        worker_init_fn=seed_worker,
        generator=torch.Generator().manual_seed(seed),
        pin_memory=torch.cuda.is_available(),
        persistent_workers=num_workers > 0,
    )


def augment_batch(x: torch.Tensor, generator: torch.Generator, pad: int = 4) -> torch.Tensor:
    n, c, h, w = x.shape
    padded = F.pad(x.float(), (pad, pad, pad, pad), mode="reflect").to(x.dtype)
    dy = torch.randint(0, 2 * pad + 1, (n,), generator=generator).to(x.device)
    dx = torch.randint(0, 2 * pad + 1, (n,), generator=generator).to(x.device)
    flip = (torch.rand(n, generator=generator) < 0.5).to(x.device)
    rows = (dy[:, None] + torch.arange(h, device=x.device)).view(n, 1, h, 1).expand(n, c, h, w + 2 * pad)
    cols = (dx[:, None] + torch.arange(w, device=x.device)).view(n, 1, 1, w).expand(n, c, h, w)
    out = padded.gather(2, rows).gather(3, cols)
    return torch.where(flip.view(n, 1, 1, 1), out.flip(3), out)
