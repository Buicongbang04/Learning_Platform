"""Pipeline dữ liệu CIFAR-10: decode một lần, Dataset có augmentation, worker có seed, augmentation theo batch.

Chạy test: uv run pytest tracks/ai-engineer/modules/02-pytorch-deep-dive/exercises/basic/03-fast-dataloader -q
"""

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
    """Đọc một tệp parquet CIFAR-10 (cột `img` là dict {"bytes": PNG, ...}, cột `label`), decode MỌI ảnh một lần.

    Trả (images uint8 shape (N, 3, 32, 32) contiguous, labels int64 shape (N,)), giữ thứ tự dòng.
    """
    # TODO
    raise NotImplementedError


class CifarDataset(Dataset):
    """Dataset trên tensor uint8 đã decode.

    __getitem__(i) trả (x float32 (3, 32, 32) đã chuẩn hoá (x/255 - CIFAR_MEAN) / CIFAR_STD theo kênh, nhãn int).
    augment=True: TRƯỚC khi chuẩn hoá, pad 4 pixel kiểu reflect, cắt ngẫu nhiên 32x32 (dy, dx trong 0..8),
    rồi lật ngang với xác suất 0.5. Mọi số ngẫu nhiên lấy từ self.rng = np.random.default_rng(seed).
    """

    def __init__(self, images: torch.Tensor, labels: torch.Tensor, augment: bool = False, seed: int = 0):
        # TODO
        raise NotImplementedError

    def __len__(self) -> int:
        # TODO
        raise NotImplementedError

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        # TODO
        raise NotImplementedError


def seed_worker(worker_id: int) -> None:
    """worker_init_fn: mỗi worker phải có dòng số ngẫu nhiên riêng cho `rng` của dataset,
    mà vẫn tái lập được theo seed của DataLoader."""
    # TODO
    raise NotImplementedError


def make_loader(dataset: Dataset, batch_size: int, shuffle: bool, num_workers: int, seed: int) -> DataLoader:
    """DataLoader tái lập được: cùng seed thì cùng thứ tự VÀ cùng augmentation, kể cả khi num_workers > 0.

    Dùng generator có seed, worker_init_fn=seed_worker, pin_memory khi có CUDA,
    persistent_workers khi num_workers > 0.
    """
    # TODO
    raise NotImplementedError


def augment_batch(x: torch.Tensor, generator: torch.Generator, pad: int = 4) -> torch.Tensor:
    """Augmentation cho CẢ BATCH (N, C, H, W) cùng lúc, không vòng lặp Python theo ảnh, chạy được trên GPU.

    Mỗi ảnh: pad `pad` pixel kiểu reflect, cắt H x W tại (dy, dx) ngẫu nhiên trong 0..2*pad, lật ngang với
    xác suất 0.5. Số ngẫu nhiên sinh trên CPU từ `generator` (rồi chuyển sang device của x). Giữ dtype của x.
    """
    # TODO
    raise NotImplementedError
