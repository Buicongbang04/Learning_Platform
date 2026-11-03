"""Freshness của feature online: từ event time tới lúc giá trị đọc được trong online store."""

import numpy as np


def freshness(records: list[dict]) -> dict:
    if not records:
        return {"n": 0, "p50": None, "p95": None}
    lag = np.array([r["visible_at"] - r["event_time"] for r in records], dtype=float)
    return {"n": len(lag), "p50": float(np.percentile(lag, 50)), "p95": float(np.percentile(lag, 95))}
