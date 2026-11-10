import math
from dataclasses import dataclass, field

DEFAULT_POLICY = {
    "min_improvement": 0.01,
    "slice_tolerance": 0.05,
    "min_slice_n": 200,
    "max_latency_ratio": 1.2,
    "max_latency_ms": None,
    "max_mae": None,
}


@dataclass
class Decision:
    promote: bool
    reasons: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)


def _finite(*values) -> bool:
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def _check_overall(challenger, champion, policy, reasons):
    mae = challenger.get("mae")
    if champion is None:
        limit = policy["max_mae"]
        if not _finite(mae) or (limit is not None and mae > limit):
            reasons.append(f"MAE {mae} không đạt ngưỡng tuyệt đối {limit}")
            return False
        return True
    if not _finite(mae, champion.get("mae")):
        reasons.append(f"MAE không hợp lệ: challenger={mae}, champion={champion.get('mae')}")
        return False
    gain = (champion["mae"] - mae) / champion["mae"]
    if gain + 1e-12 < policy["min_improvement"]:
        reasons.append(f"MAE tổng cải thiện {gain:.2%}, cần ít nhất {policy['min_improvement']:.2%}")
        return False
    return True


def _check_slices(challenger, champion, policy, reasons):
    if champion is None:
        return True
    ok = True
    mine = challenger.get("slices") or {}
    for name, base in sorted((champion.get("slices") or {}).items()):
        if name not in mine:
            reasons.append(f"slice '{name}' thiếu ở challenger, không kiểm được")
            ok = False
            continue
        if min(base["n"], mine[name]["n"]) < policy["min_slice_n"]:
            continue
        if not _finite(mine[name]["mae"], base["mae"]):
            reasons.append(f"slice '{name}': MAE không hợp lệ")
            ok = False
            continue
        worse = (mine[name]["mae"] - base["mae"]) / base["mae"]
        if worse - 1e-12 > policy["slice_tolerance"]:
            reasons.append(f"slice '{name}' xấu đi {worse:.2%}, vượt dung sai {policy['slice_tolerance']:.2%}")
            ok = False
    return ok


def _check_latency(challenger, champion, policy, reasons):
    latency = challenger.get("latency_p95_ms")
    if not _finite(latency):
        reasons.append("thiếu latency_p95_ms của challenger")
        return False
    ok = True
    if champion is not None and latency > champion["latency_p95_ms"] * policy["max_latency_ratio"] + 1e-12:
        reasons.append(
            f"latency p95 {latency:.1f} ms quá {policy['max_latency_ratio']}x của champion ({champion['latency_p95_ms']:.1f} ms)")
        ok = False
    if policy["max_latency_ms"] is not None and latency > policy["max_latency_ms"]:
        reasons.append(f"latency p95 {latency:.1f} ms vượt trần {policy['max_latency_ms']} ms")
        ok = False
    return ok


def decide_promotion(challenger: dict, champion: dict | None, policy: dict | None = None) -> Decision:
    merged = {**DEFAULT_POLICY, **(policy or {})}
    reasons: list[str] = []
    checks = {
        "overall_mae": _check_overall(challenger, champion, merged, reasons),
        "slices": _check_slices(challenger, champion, merged, reasons),
        "latency": _check_latency(challenger, champion, merged, reasons),
    }
    promote = all(checks.values())
    if promote:
        reasons.append("đạt cả ba cổng: MAE tổng, slice, latency" if champion else "chưa có champion, đạt ngưỡng tuyệt đối")
    return Decision(promote=promote, reasons=reasons, checks=checks)
