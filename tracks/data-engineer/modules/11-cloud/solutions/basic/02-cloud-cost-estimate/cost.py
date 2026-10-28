"""Ước tính hoá đơn cloud: lưu trữ, egress, scan. Giá minh hoạ, không phải bảng giá chính thức."""

from __future__ import annotations

import math

TB = 1024  # GB

# (giới hạn trên cộng dồn tính bằng GB, giá USD mỗi GB)
EGRESS_TIERS: list[tuple[float, float]] = [
    (100, 0.0),
    (10 * TB, 0.09),
    (50 * TB, 0.085),
    (150 * TB, 0.07),
    (math.inf, 0.05),
]


def _non_negative(**values: float) -> None:
    for name, value in values.items():
        if value < 0:
            raise ValueError(f"{name} không được âm (nhận {value})")


def storage_cost(gb: float, price_per_gb_month: float = 0.023, months: float = 1) -> float:
    _non_negative(gb=gb, months=months, price_per_gb_month=price_per_gb_month)
    return gb * price_per_gb_month * months


def egress_cost(gb: float, tiers: list[tuple[float, float]] = EGRESS_TIERS) -> float:
    _non_negative(gb=gb)
    total, lower = 0.0, 0.0
    for upper, price in tiers:
        portion = min(gb, upper) - lower
        if portion > 0:
            total += portion * price
        if gb <= upper:
            break
        lower = upper
    return total


def scan_cost(tb_scanned: float, price_per_tb: float = 6.25, free_tb: float = 1.0) -> float:
    _non_negative(tb_scanned=tb_scanned)
    return max(0.0, tb_scanned - free_tb) * price_per_tb


def monthly_bill(storage_gb: float, egress_gb: float, scanned_tb: float,
                 storage_price: float = 0.023) -> dict[str, float]:
    bill = {
        "storage": round(storage_cost(storage_gb, storage_price), 2),
        "egress": round(egress_cost(egress_gb), 2),
        "scan": round(scan_cost(scanned_tb), 2),
    }
    bill["total"] = round(bill["storage"] + bill["egress"] + bill["scan"], 2)
    return bill
