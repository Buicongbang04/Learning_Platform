"""Phát hiện thiên lệch do model tự gây: nhãn chỉ có ở giao dịch model cho qua."""


def naive_rate(log: list[dict]) -> float | None:
    labels = [row["label"] for row in log if row["label"] is not None]
    return sum(labels) / len(labels) if labels else None


def ipw_rate(log: list[dict]) -> float | None:
    if not log or any(row["p_approve"] <= 0 for row in log):
        return None
    return sum(row["label"] / row["p_approve"] for row in log if row["label"] is not None) / len(log)


def bias_report(log: list[dict], tolerance: float = 0.01) -> dict:
    naive, ipw = naive_rate(log), ipw_rate(log)
    if naive is None or ipw is None:
        return {"naive": naive, "ipw": ipw, "gap": None, "biased": None}
    gap = naive - ipw
    return {"naive": naive, "ipw": ipw, "gap": gap, "biased": abs(gap) > tolerance}


def per_round(log: list[dict], tolerance: float = 0.01) -> list[dict]:
    rounds = sorted({row["round"] for row in log})
    return [dict(bias_report([row for row in log if row["round"] == r], tolerance), round=r) for r in rounds]
