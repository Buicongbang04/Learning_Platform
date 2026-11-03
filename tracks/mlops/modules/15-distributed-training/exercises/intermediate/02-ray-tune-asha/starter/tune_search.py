"""Tìm siêu tham số cho MLP nhỏ bằng Ray Tune, dừng sớm trial kém bằng ASHA.

Chạy thử: RAY_ENABLE_UV_RUN_RUNTIME_ENV=0 RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=0 uv run python tune_search.py
"""

import tempfile

import torch
from ray import tune
from ray.tune.result_grid import ResultGrid
from ray.tune.schedulers import ASHAScheduler
from torch import nn

SEED = 3
FEATURES = 8
MAX_EPOCHS = 16
BATCH = 64
LR_RANGE = (1e-3, 0.3)
HIDDEN_CHOICES = [4, 16, 64]


def make_data(seed: int = SEED) -> tuple[torch.Tensor, ...]:
    gen = torch.Generator().manual_seed(seed)
    x = torch.randn(768, FEATURES, generator=gen)
    y = 0.5 * x[:, :3].sum(dim=1, keepdim=True) + 0.3 * torch.relu(x[:, 3:4]) + 0.1 * torch.randn(768, 1, generator=gen)
    return x[:512], y[:512], x[512:], y[512:]


def build_model(hidden: int) -> nn.Module:
    torch.manual_seed(SEED)
    return nn.Sequential(nn.Linear(FEATURES, hidden), nn.ReLU(), nn.Linear(hidden, 1))


def train_model(config: dict) -> None:
    """Trainable của Tune: `build_model(config["hidden"])`, SGD lr `config["lr"]`, MAX_EPOCHS epoch; báo {"loss": ...} mỗi epoch."""
    # TODO
    raise NotImplementedError


def search(storage_path: str, num_samples: int = 12) -> ResultGrid:
    """Chạy `num_samples` trial trên không gian tìm kiếm của README với scheduler ASHA; lưu kết quả dưới `storage_path`."""
    # TODO
    raise NotImplementedError


def best(results: ResultGrid) -> dict:
    """{"config": config của trial tốt nhất, "loss": loss cuối cùng của trial đó}."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    import ray

    ray.init(num_cpus=2, include_dashboard=False, _node_ip_address="127.0.0.1")
    with tempfile.TemporaryDirectory() as storage:
        grid = search(storage)
        print(best(grid))
