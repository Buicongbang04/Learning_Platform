import csv
import math
from pathlib import Path

import yaml

FIELDS = ("workload", "team", "env", "replicas", "hours", "cpu_request_m", "mem_request_mi", "cpu_p95_m", "mem_max_mi")
NUMBERS = FIELDS[3:]
UNALLOCATED = "unallocated"


def load_usage(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError(f"Cột phải là {FIELDS}")
        rows = []
        for line in reader:
            row = {"workload": line["workload"], "team": line["team"] or None, "env": line["env"]}
            row.update({key: int(line[key]) for key in NUMBERS})
            if any(row[key] < 0 for key in NUMBERS):
                raise ValueError(f"{row['workload']}: số âm")
            rows.append(row)
    return rows


def load_pricing(path: Path) -> dict:
    pricing = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for key in ("vcpu_hour", "gib_hour", "orders"):
        if not isinstance(pricing.get(key), (int, float)) or pricing[key] <= 0:
            raise ValueError(f"pricing thiếu {key}")
    return pricing


def cost(row: dict, pricing: dict, cpu_m: int | None = None, mem_mi: int | None = None) -> float:
    cpu = row["cpu_request_m"] if cpu_m is None else cpu_m
    mem = row["mem_request_mi"] if mem_mi is None else mem_mi
    return row["replicas"] * row["hours"] * (cpu / 1000 * pricing["vcpu_hour"] + mem / 1024 * pricing["gib_hour"])


def _step(value: float, step: int, floor: int) -> int:
    return max(floor, math.ceil(value / step) * step)


def rightsize(row: dict, headroom: float = 0.2) -> dict:
    cpu = _step(row["cpu_p95_m"] * (1 + headroom), 50, 50)
    mem = _step(row["mem_max_mi"] * (1 + headroom), 64, 128)
    if cpu > row["cpu_request_m"] or mem > row["mem_request_mi"]:
        action = "up"
    elif cpu == row["cpu_request_m"] and mem == row["mem_request_mi"]:
        action = "keep"
    else:
        action = "down"
    return {"cpu_m": cpu, "mem_mi": mem, "action": action}


def allocate(rows: list[dict], pricing: dict) -> dict[str, float]:
    direct: dict[str, float] = {}
    for row in rows:
        team = row["team"] or UNALLOCATED
        direct[team] = direct.get(team, 0.0) + cost(row, pricing)
    total = sum(direct.values())
    shared = sum((pricing.get("shared") or {}).values())
    return {team: round(value + shared * value / total, 2) for team, value in sorted(direct.items())}


def savings(rows: list[dict], pricing: dict) -> float:
    total = 0.0
    for row in rows:
        new = rightsize(row)
        total += cost(row, pricing) - cost(row, pricing, new["cpu_m"], new["mem_mi"])
    return round(total, 2)


def idle(rows: list[dict], cpu_ratio: float = 0.05, mem_ratio: float = 0.2) -> list[tuple[str, str]]:
    return sorted((r["workload"], r["env"]) for r in rows
                  if r["cpu_p95_m"] < cpu_ratio * r["cpu_request_m"] and r["mem_max_mi"] < mem_ratio * r["mem_request_mi"])


def unit_cost(rows: list[dict], pricing: dict) -> float:
    total = sum(cost(r, pricing) for r in rows) + sum((pricing.get("shared") or {}).values())
    return round(total / (pricing["orders"] / 1000), 4)
