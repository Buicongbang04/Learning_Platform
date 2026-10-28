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


def storage_cost(gb: float, price_per_gb_month: float = 0.023, months: float = 1) -> float:
    # TODO 1: gb * giá * months; gb hoặc months âm -> ValueError
    raise NotImplementedError


def egress_cost(gb: float, tiers: list[tuple[float, float]] = EGRESS_TIERS) -> float:
    # TODO 2: tính lũy tiến theo bậc; gb âm -> ValueError
    raise NotImplementedError


def scan_cost(tb_scanned: float, price_per_tb: float = 6.25, free_tb: float = 1.0) -> float:
    # TODO 3: phần vượt free_tb nhân giá, không âm; tb_scanned âm -> ValueError
    raise NotImplementedError


def monthly_bill(storage_gb: float, egress_gb: float, scanned_tb: float,
                 storage_price: float = 0.023) -> dict[str, float]:
    # TODO 4: dict storage, egress, scan, total (làm tròn 2 chữ số)
    raise NotImplementedError
