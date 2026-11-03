LATENCY_THRESHOLD_MS = 300
TARGETS = {"availability": 0.995, "latency_ok": 0.99}


def _root(trace: dict) -> dict:
    return next(s for s in trace["spans"] if s.get("parent") is None)


def _measured(traces: list[dict]) -> list[dict]:
    return [_root(trace) for trace in traces]


def availability(traces: list[dict]) -> tuple[float | None, int]:
    """(tỉ lệ thành công, số sự kiện trong mẫu số)."""
    spans = _measured(traces)
    if not spans:
        return None, 0
    return sum(1 for s in spans if s["status"] < 500) / len(spans), len(spans)


def latency_ok(traces: list[dict], threshold_ms: float = LATENCY_THRESHOLD_MS) -> tuple[float | None, int]:
    """(tỉ lệ yêu cầu thành công trả lời trong ngưỡng, số sự kiện trong mẫu số)."""
    served = [s for s in _measured(traces) if s["status"] < 500]
    if not served:
        return None, 0
    return sum(1 for s in served if s["duration_ms"] <= threshold_ms) / len(served), len(served)


def slo_report(traces: list[dict], targets: dict = TARGETS) -> dict:
    """{tên SLI: {"value", "events", "target", "met"}}."""
    report = {}
    for name, fn in (("availability", availability), ("latency_ok", latency_ok)):
        value, events = fn(traces)
        report[name] = {"value": value, "events": events, "target": targets[name],
                        "met": value is not None and value >= targets[name]}
    return report
