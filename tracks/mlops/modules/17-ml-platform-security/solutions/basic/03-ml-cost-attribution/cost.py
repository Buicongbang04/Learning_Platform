"""Cost attribution cho nền tảng ML: chi phí trực tiếp theo đội và model, chi phí idle, showback, chargeback."""

import csv
from collections import defaultdict
from pathlib import Path

RESOURCES = {"cpu_hours": "cpu_hour", "gpu_hours": "gpu_hour", "mem_gb_hours": "mem_gb_hour"}
UNALLOCATED = "unallocated"
UNLABELLED = "unlabelled"


def load_usage(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row = {"date": raw["date"], "namespace": raw["namespace"], "model": raw["model"].strip() or None,
                   "workload": raw["workload"]}
            row.update({key: float(raw[key]) for key in RESOURCES})
            rows.append(row)
    return rows


def row_cost(row: dict, prices: dict) -> float:
    return sum(row[key] * prices[price] for key, price in RESOURCES.items())


def owner_of(row: dict, config: dict) -> tuple[str, str]:
    team = config["namespaces"].get(row["namespace"], UNALLOCATED)
    return team, row["model"] or UNLABELLED


def cost_by_model(rows: list[dict], config: dict) -> dict[tuple[str, str], float]:
    totals = defaultdict(float)
    for row in rows:
        totals[owner_of(row, config)] += row_cost(row, config["prices"])
    return dict(totals)


def idle_cost(rows: list[dict], config: dict) -> float:
    total = 0.0
    for key, price in RESOURCES.items():
        used = sum(row[key] for row in rows)
        total += max(0.0, config["capacity"][key] - used) * config["prices"][price]
    return total


def showback(rows: list[dict], config: dict) -> dict[str, dict[str, float]]:
    direct = defaultdict(float)
    for (team, _), cost in cost_by_model(rows, config).items():
        direct[team] += cost
    idle = idle_cost(rows, config)
    shared_base = sum(cost for team, cost in direct.items() if team != UNALLOCATED)
    report = {}
    for team, cost in direct.items():
        share = 0.0 if team == UNALLOCATED or shared_base == 0 else idle * cost / shared_base
        report[team] = {"direct": cost, "idle_share": share, "total": cost + share}
    return report


def chargeback(rows: list[dict], config: dict) -> list[dict]:
    lines = []
    for team, item in showback(rows, config).items():
        center = "UNALLOCATED" if team == UNALLOCATED else config["cost_centers"][team]
        lines.append({"cost_center": center, "team": team, "amount": round(item["total"], 2)})
    return sorted(lines, key=lambda line: line["cost_center"])
