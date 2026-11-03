import math
from pathlib import Path

import yaml

MARKETS = ("on_demand", "spot")


def load_prices(path: Path) -> dict[str, dict[str, float | None]]:
    """Đọc bảng giá YAML, trả {gpu: {"on_demand": float, "spot": float | None}}; dữ liệu sai thì ValueError."""
    # TODO
    raise NotImplementedError


def scaling_efficiency(throughput_1: float, throughput_n: float, n: int) -> float:
    """Hiệu suất scale: thông lượng n GPU so với n lần thông lượng 1 GPU."""
    # TODO
    raise NotImplementedError


def wall_hours(single_gpu_hours: float, n_gpus: int, efficiency: float) -> float:
    """Số giờ đồng hồ khi chạy trên n_gpus với hiệu suất efficiency."""
    # TODO
    raise NotImplementedError


def spot_overhead_hours(hours: float, preemptions_per_hour: float, checkpoint_every_h: float, restart_h: float) -> float:
    """Số giờ chạy thêm kỳ vọng vì bị thu hồi spot trong `hours` giờ chạy."""
    # TODO
    raise NotImplementedError


def estimate(prices: dict, gpu: str, n_gpus: int, single_gpu_hours: float, efficiency: float, market: str = "on_demand",
             preemptions_per_hour: float = 0.0, checkpoint_every_h: float = 1.0, restart_h: float = 0.0) -> dict:
    """{"wall_hours", "gpu_hours", "cost"} của một phương án, theo công thức trong README."""
    # TODO
    raise NotImplementedError


def cheapest(prices: dict, plans: list[dict], deadline_h: float) -> dict | None:
    """Phương án rẻ nhất xong trước deadline: {"name", "wall_hours", "gpu_hours", "cost"}; không có thì None."""
    # TODO
    raise NotImplementedError


def optimal_checkpoint_every_h(checkpoint_cost_h: float, preemptions_per_hour: float) -> float:
    """Khoảng checkpoint tối ưu theo công thức Young trong README."""
    # TODO
    raise NotImplementedError
