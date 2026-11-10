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
    options = {"prefetch_factor": prefetch_factor} if num_workers > 0 else {}
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, **options)
    iterator = iter(loader)
    wait_s = compute_s = 0.0
    for index in range(warmup + batches):
        started = time.perf_counter()
        batch = next(iterator)
        fetched = time.perf_counter()
        step(batch)
        finished = time.perf_counter()
        if index >= warmup:
            wait_s += fetched - started
            compute_s += finished - fetched
    del iterator
    total = wait_s + compute_s
    return {
        "num_workers": num_workers,
        "batches": batches,
        "wait_s": wait_s,
        "compute_s": compute_s,
        "wait_fraction": wait_s / total,
        "samples_per_s": batches * batch_size / total,
    }


def diagnose(report: dict, threshold: float = 0.2) -> str:
    return "data" if report["wait_fraction"] > threshold else "compute"


def smallest_sufficient(dataset: Dataset, candidates=(0, 1, 2, 4), **kwargs) -> tuple[int | None, list[dict]]:
    reports = []
    for workers in sorted(candidates):
        report = profile(dataset, workers, **kwargs)
        reports.append(report)
        if diagnose(report) == "compute":
            return workers, reports
    return None, reports
