def availability(events: list[dict]) -> float | None:
    """Tỉ lệ sự kiện có status < 500; None khi không có sự kiện."""
    # TODO
    raise NotImplementedError


def latency_sli(events: list[dict], threshold_ms: float) -> float | None:
    """Trong các sự kiện status < 500, tỉ lệ có latency_ms <= threshold_ms; None khi không có."""
    # TODO
    raise NotImplementedError


def quality_sli(events: list[dict], tolerance_min: float) -> float | None:
    """Trong các sự kiện đã có nhãn (abs_error_min không phải None), tỉ lệ abs_error_min <= tolerance_min; None khi không có."""
    # TODO
    raise NotImplementedError


def freshness_sli(events: list[dict], max_age_s: float) -> float | None:
    """Tỉ lệ sự kiện có feature_age_s <= max_age_s; None khi không có sự kiện."""
    # TODO
    raise NotImplementedError


def budget_minutes(slo: float, window_days: float) -> float:
    """Error budget quy ra phút: (1 - slo) x số phút của cửa sổ."""
    # TODO
    raise NotImplementedError


def error_budget(sli: float, slo: float, total: int) -> dict:
    """{"allowed_bad", "bad", "remaining"} theo công thức trong README."""
    # TODO
    raise NotImplementedError


def burn_rate(bad_ratio: float, slo: float) -> float:
    """Tốc độ đốt budget so với mức vừa hết đúng cuối cửa sổ."""
    # TODO
    raise NotImplementedError


def window_burn_rates(events: list[dict], slo: float, now: int, windows_s: list[int]) -> dict[int, float]:
    """{cửa sổ (giây): burn rate khả dụng trong [now - cửa sổ, now)}; cửa sổ không có sự kiện cho 0.0."""
    # TODO
    raise NotImplementedError
