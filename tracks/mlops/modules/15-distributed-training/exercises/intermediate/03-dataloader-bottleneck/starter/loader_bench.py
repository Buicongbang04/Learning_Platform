"""Đo vòng huấn luyện chờ dữ liệu bao lâu, chẩn đoán điểm nghẽn và chọn num_workers đủ dùng."""

import time

import torch
from torch.utils.data import DataLoader, Dataset

DECODE_S = 0.002
STEP_S = 0.02
BATCH = 16
FEATURES = 32


class SlowDataset(Dataset):
    """Mỗi mẫu tốn `decode_s` giây để "đọc và giải mã" (đứng thay cho đọc ảnh từ đĩa/S3 rồi decode, augment)."""

    def __init__(self, n: int = 4096, decode_s: float = DECODE_S):
        self.n = n
        self.decode_s = decode_s

    def __len__(self) -> int:
        return self.n

    def __getitem__(self, index: int) -> torch.Tensor:
        time.sleep(self.decode_s)
        return torch.full((FEATURES,), float(index % 97))


def train_step(batch: torch.Tensor, step_s: float = STEP_S) -> None:
    """Đứng thay cho một bước forward/backward trên GPU: chiếm `step_s` giây."""
    time.sleep(step_s)


def profile(dataset: Dataset, num_workers: int, batches: int = 25, warmup: int = 5, batch_size: int = BATCH,
            prefetch_factor: int = 2, step=train_step) -> dict:
    """Chạy vòng huấn luyện `warmup + batches` batch, đo riêng thời gian chờ batch và thời gian `step`; trả dict theo README."""
    # TODO
    raise NotImplementedError


def diagnose(report: dict, threshold: float = 0.2) -> str:
    """"data" nếu vòng huấn luyện chờ dữ liệu quá `threshold` thời gian, ngược lại "compute"."""
    # TODO
    raise NotImplementedError


def smallest_sufficient(dataset: Dataset, candidates=(0, 1, 2, 4), **kwargs) -> tuple[int | None, list[dict]]:
    """num_workers nhỏ nhất trong `candidates` mà điểm nghẽn không còn là dữ liệu, kèm các report đã đo."""
    # TODO
    raise NotImplementedError
