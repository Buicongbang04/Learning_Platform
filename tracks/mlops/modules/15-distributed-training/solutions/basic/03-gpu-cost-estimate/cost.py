import math
from pathlib import Path

import yaml

MARKETS = ("on_demand", "spot")


def load_prices(path: Path) -> dict[str, dict[str, float | None]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    gpus = data.get("gpus")
    if not isinstance(gpus, dict) or not gpus:
        raise ValueError("bảng giá thiếu mục gpus")
    table = {}
    for name, row in gpus.items():
        if not isinstance(row, dict):
            raise ValueError(f"{name}: dòng giá không hợp lệ")
        on_demand, spot = row.get("on_demand"), row.get("spot")
        if not isinstance(on_demand, (int, float)) or isinstance(on_demand, bool) or on_demand <= 0:
            raise ValueError(f"{name}: on_demand phải là số dương")
        if spot is not None and (not isinstance(spot, (int, float)) or isinstance(spot, bool) or spot <= 0):
            raise ValueError(f"{name}: spot phải là số dương hoặc null")
        table[name] = {"on_demand": float(on_demand), "spot": None if spot is None else float(spot)}
    return table


def scaling_efficiency(throughput_1: float, throughput_n: float, n: int) -> float:
    return throughput_n / (n * throughput_1)


def wall_hours(single_gpu_hours: float, n_gpus: int, efficiency: float) -> float:
    if n_gpus < 1 or not 0 < efficiency <= 1:
        raise ValueError("n_gpus >= 1 và 0 < efficiency <= 1")
    return single_gpu_hours / (n_gpus * efficiency)


def spot_overhead_hours(hours: float, preemptions_per_hour: float, checkpoint_every_h: float, restart_h: float) -> float:
    return hours * preemptions_per_hour * (checkpoint_every_h / 2 + restart_h)


def estimate(prices: dict, gpu: str, n_gpus: int, single_gpu_hours: float, efficiency: float, market: str = "on_demand",
             preemptions_per_hour: float = 0.0, checkpoint_every_h: float = 1.0, restart_h: float = 0.0) -> dict:
    if gpu not in prices:
        raise ValueError(f"không có giá cho {gpu}")
    if market not in MARKETS:
        raise ValueError(f"market phải thuộc {MARKETS}")
    price = prices[gpu][market]
    if price is None:
        raise ValueError(f"{gpu} không có giá {market}")
    wall = wall_hours(single_gpu_hours, n_gpus, efficiency)
    if market == "spot":
        wall += spot_overhead_hours(wall, preemptions_per_hour, checkpoint_every_h, restart_h)
    gpu_hours = wall * n_gpus
    return {"wall_hours": wall, "gpu_hours": gpu_hours, "cost": gpu_hours * price}


def cheapest(prices: dict, plans: list[dict], deadline_h: float) -> dict | None:
    best = None
    for plan in plans:
        try:
            result = estimate(prices, **{k: v for k, v in plan.items() if k != "name"})
        except ValueError:
            continue
        if result["wall_hours"] > deadline_h:
            continue
        key = (result["cost"], result["wall_hours"])
        if best is None or key < best[0]:
            best = (key, {"name": plan["name"], **result})
    return None if best is None else best[1]


def optimal_checkpoint_every_h(checkpoint_cost_h: float, preemptions_per_hour: float) -> float:
    if preemptions_per_hour <= 0:
        return math.inf
    return math.sqrt(2 * checkpoint_cost_h / preemptions_per_hour)
