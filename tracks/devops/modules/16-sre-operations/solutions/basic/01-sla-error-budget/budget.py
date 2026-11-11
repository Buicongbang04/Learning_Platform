import csv
import math
from pathlib import Path

FIELDS = ("hour", "requests", "errors", "slow", "maintenance")


def load(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError(f"Cột phải là {FIELDS}")
        rows = []
        for line in reader:
            row = {"hour": line["hour"], "requests": int(line["requests"]), "errors": int(line["errors"]),
                   "slow": int(line["slow"]), "maintenance": line["maintenance"] == "1"}
            if row["requests"] < 0 or not 0 <= row["errors"] + row["slow"] <= row["requests"]:
                raise ValueError(f"Dòng {row['hour']}: errors + slow phải nằm trong [0, requests]")
            rows.append(row)
    return rows


def _bad(row: dict) -> int:
    return row["errors"] + row["slow"]


def sli(rows: list[dict]) -> float:
    total = sum(r["requests"] for r in rows)
    if total == 0:
        raise ValueError("Không có request nào")
    return 1 - sum(_bad(r) for r in rows) / total


def budget_report(rows: list[dict], slo: float) -> dict:
    if not 0 < slo < 1:
        raise ValueError("slo phải nằm trong (0, 1)")
    total = sum(r["requests"] for r in rows)
    if total == 0:
        raise ValueError("Không có request nào")
    bad = sum(_bad(r) for r in rows)
    allowed = (1 - slo) * total
    exhausted_at = None
    running = 0
    for row in rows:
        running += _bad(row)
        if running > allowed:
            exhausted_at = row["hour"]
            break
    return {"total": total, "bad": bad, "allowed_bad": allowed, "consumed": bad / allowed,
            "remaining": 1 - bad / allowed, "exhausted_at": exhausted_at}


def burn_rates(rows: list[dict], slo: float, end_hour: str, windows=(1, 6, 24, 72)) -> dict[int, float]:
    hours = [r["hour"] for r in rows]
    if end_hour not in hours:
        raise ValueError(f"Không có giờ {end_hour}")
    end = hours.index(end_hour) + 1
    result = {}
    for window in windows:
        if window < 1 or window > end:
            raise ValueError(f"Cửa sổ {window} giờ vượt dữ liệu")
        part = rows[end - window:end]
        total = sum(r["requests"] for r in part)
        result[window] = (sum(_bad(r) for r in part) / total) / (1 - slo) if total else 0.0
    return result


def sla_availability(rows: list[dict], threshold: float = 0.05) -> float:
    counted = [r for r in rows if not r["maintenance"]]
    if not counted:
        raise ValueError("Không còn giờ nào sau khi bỏ bảo trì")
    down = sum(1 for r in counted if r["requests"] and r["errors"] / r["requests"] > threshold)
    return 1 - down / len(counted)


def sla_credit(availability: float, tiers) -> int:
    for floor, credit in sorted(tiers, reverse=True):
        if availability * 100 >= floor:
            return credit
    raise ValueError("Bảng tier phải có mức 0")


def policy(report: dict) -> str:
    remaining = report["remaining"]
    if remaining <= 0:
        return "freeze"
    if remaining <= 0.5:
        return "caution"
    return "normal"

