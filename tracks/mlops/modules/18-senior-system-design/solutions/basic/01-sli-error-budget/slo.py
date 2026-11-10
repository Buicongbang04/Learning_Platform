def _ratio(good: int, total: int) -> float | None:
    return good / total if total else None


def availability(events: list[dict]) -> float | None:
    """Tỉ lệ sự kiện có status < 500; None khi không có sự kiện."""
    return _ratio(sum(1 for e in events if e["status"] < 500), len(events))


def latency_sli(events: list[dict], threshold_ms: float) -> float | None:
    """Trong các sự kiện status < 500, tỉ lệ có latency_ms <= threshold_ms; None khi không có."""
    served = [e for e in events if e["status"] < 500]
    return _ratio(sum(1 for e in served if e["latency_ms"] <= threshold_ms), len(served))


def quality_sli(events: list[dict], tolerance_min: float) -> float | None:
    """Trong các sự kiện đã có nhãn (abs_error_min không phải None), tỉ lệ abs_error_min <= tolerance_min; None khi không có."""
    labelled = [e["abs_error_min"] for e in events if e.get("abs_error_min") is not None]
    return _ratio(sum(1 for err in labelled if err <= tolerance_min), len(labelled))


def freshness_sli(events: list[dict], max_age_s: float) -> float | None:
    """Tỉ lệ sự kiện có feature_age_s <= max_age_s; None khi không có sự kiện."""
    return _ratio(sum(1 for e in events if e["feature_age_s"] <= max_age_s), len(events))


def budget_minutes(slo: float, window_days: float) -> float:
    """Error budget quy ra phút: (1 - slo) x số phút của cửa sổ."""
    return (1 - slo) * window_days * 24 * 60


def error_budget(sli: float, slo: float, total: int) -> dict:
    """{"allowed_bad", "bad", "remaining"} theo công thức trong README."""
    allowed = (1 - slo) * total
    bad = (1 - sli) * total
    return {"allowed_bad": allowed, "bad": bad, "remaining": 1 - bad / allowed}


def burn_rate(bad_ratio: float, slo: float) -> float:
    """Tốc độ đốt budget so với mức vừa hết đúng cuối cửa sổ."""
    return bad_ratio / (1 - slo)


def window_burn_rates(events: list[dict], slo: float, now: int, windows_s: list[int]) -> dict[int, float]:
    """{cửa sổ (giây): burn rate khả dụng trong [now - cửa sổ, now)}; cửa sổ không có sự kiện cho 0.0."""
    rates = {}
    for window in windows_s:
        inside = [e for e in events if now - window <= e["ts"] < now]
        value = availability(inside)
        rates[window] = 0.0 if value is None else burn_rate(1 - value, slo)
    return rates
