"""Chi phí theo model trên cụm dùng chung: trực tiếp theo request, idle chia theo tỉ lệ, phần không gắn đội tách riêng."""

import csv
from collections import defaultdict
from pathlib import Path

RESOURCES = {"cpu_hours": "cpu_hour", "gpu_hours": "gpu_hour", "mem_gb_hours": "mem_gb_hour"}
UNLABELLED = "unlabelled"


def load_usage(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row = {"date": raw["date"], "namespace": raw["namespace"].strip(), "model": raw["model"].strip() or None,
                   "workload": raw["workload"]}
            row.update({key: float(raw[key]) for key in RESOURCES})
            rows.append(row)
    return rows


def row_cost(row: dict, prices: dict) -> float:
    return sum(row[key] * prices[price] for key, price in RESOURCES.items())


def cost_report(rows: list[dict], config: dict) -> dict:
    prices, capacity = config["prices"], config["capacity"]
    direct, unallocated = defaultdict(float), 0.0
    for row in rows:
        team = config["namespaces"].get(row["namespace"])
        if team is None:
            unallocated += row_cost(row, prices)
        else:
            direct[(team, row["model"] or UNLABELLED)] += row_cost(row, prices)
    idle = sum(max(0.0, capacity[key] - sum(r[key] for r in rows)) * prices[price] for key, price in RESOURCES.items())
    base = sum(direct.values())
    models = []
    for (team, model), cost in sorted(direct.items()):
        share = idle * cost / base if base else 0.0
        models.append({"team": team, "model": model, "cost_center": config["cost_centers"][team],
                       "direct": round(cost, 2), "idle_share": round(share, 2), "total": round(cost + share, 2)})
    capacity_cost = sum(capacity[key] * prices[price] for key, price in RESOURCES.items())
    return {"period": config["period"], "currency": config["currency"], "models": models,
            "unallocated": round(unallocated, 2), "idle": round(idle, 2), "capacity_cost": round(capacity_cost, 2),
            "total": round(base + idle + unallocated, 2)}


def render_markdown(report: dict) -> str:
    lines = [f"# Chi phí theo model, {report['period']} ({report['currency']})", "",
             "Sinh bằng `python -m eta.platform cost`, không sửa tay. Chi phí tính theo tài nguyên đã xin (request).", "",
             "| Đội | Model | Cost center | Trực tiếp | Phần idle | Tổng |", "| --- | --- | --- | ---: | ---: | ---: |"]
    for m in report["models"]:
        lines.append(f"| {m['team']} | {m['model']} | {m['cost_center']} | {m['direct']:.2f} | {m['idle_share']:.2f} | {m['total']:.2f} |")
    lines += ["", f"- Không gắn đội (`UNALLOCATED`): {report['unallocated']:.2f}",
              f"- Idle của cụm (đã chia vào các model theo tỉ lệ chi phí trực tiếp): {report['idle']:.2f}",
              f"- Năng lực đã cấp: {report['capacity_cost']:.2f}", f"- Tổng: {report['total']:.2f}", ""]
    return "\n".join(lines)
