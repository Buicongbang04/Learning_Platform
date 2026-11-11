import math


def _metric(summary: dict, name: str, step: int) -> dict:
    key = f"{name}{{scenario:step_{step}}}"
    metric = (summary.get("metrics") or {}).get(key)
    if metric is None:
        raise ValueError(f"Tóm tắt k6 không có {key}: thêm threshold cho submetric này trong load.js")
    return metric["values"]


def step_metrics(summary: dict, steps: list[int], step_seconds: float) -> list[dict]:
    rows = []
    for step in sorted(steps):
        duration = _metric(summary, "http_req_duration", step)
        failed = _metric(summary, "http_req_failed", step)
        count = _metric(summary, "http_reqs", step)["count"]
        rows.append({"rps": step, "achieved_rps": count / step_seconds, "p95_ms": duration["p(95)"], "avg_ms": duration["avg"],
                     "error_rate": failed["rate"]})
    return rows


def knee(rows: list[dict], slo_p95_ms: float = 200, max_error_rate: float = 0.01, min_achieved: float = 0.9) -> int | None:
    best = None
    for row in sorted(rows, key=lambda r: r["rps"]):
        healthy = (row["p95_ms"] <= slo_p95_ms and row["error_rate"] <= max_error_rate
                   and row["achieved_rps"] >= min_achieved * row["rps"])
        if not healthy:
            break
        best = row["rps"]
    return best


def littles_law(rps: float, avg_ms: float) -> float:
    return rps * avg_ms / 1000


def replicas(peak_rps: float, knee_rps: float, headroom: float = 0.3, spare: int = 1) -> int:
    if knee_rps <= 0:
        raise ValueError("knee_rps phải dương")
    return math.ceil(peak_rps * (1 + headroom) / knee_rps) + spare


def report(summary: dict, steps: list[int], step_seconds: float, peak_rps: float, slo_p95_ms: float = 200) -> str:
    rows = step_metrics(summary, steps, step_seconds)
    point = knee(rows, slo_p95_ms)
    lines = ["| Bước (rps) | Đạt được (rps) | p95 (ms) | Trung bình (ms) | Lỗi (%) |", "| --- | --- | --- | --- | --- |"]
    for row in rows:
        lines.append(f"| {row['rps']} | {row['achieved_rps']:.1f} | {row['p95_ms']:.1f} | {row['avg_ms']:.1f} | "
                     f"{row['error_rate'] * 100:.2f} |")
    lines.append("")
    if point is None:
        lines.append("Điểm gãy: không có")
        return "\n".join(lines) + "\n"
    at = next(r for r in rows if r["rps"] == point)
    lines.append(f"Điểm gãy: {point} rps")
    lines.append(f"Đồng thời ở điểm gãy (Little): {littles_law(point, at['avg_ms']):.2f}")
    lines.append(f"Replica cho đỉnh {peak_rps:g} rps: {replicas(peak_rps, point)}")
    return "\n".join(lines) + "\n"
