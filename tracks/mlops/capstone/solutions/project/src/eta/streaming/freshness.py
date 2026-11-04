"""Freshness của feature online: từ event time tới lúc giá trị đọc được, cùng một trục thời gian (mô phỏng)."""

import numpy as np


def freshness(records: list[dict]) -> dict:
    if not records:
        return {"n": 0, "p50": None, "p95": None, "max": None}
    lag = np.array([r["visible_at"] - r["event_time"] for r in records], dtype=float)
    return {"n": int(lag.size), "p50": float(np.percentile(lag, 50)), "p95": float(np.percentile(lag, 95)),
            "max": float(lag.max())}
