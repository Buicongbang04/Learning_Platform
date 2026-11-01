from datetime import datetime, timedelta


def _parse(value: str) -> datetime:
    ts = datetime.fromisoformat(value)
    if ts.utcoffset() is None:
        raise ValueError(f"Thời điểm thiếu múi giờ: {value!r}")
    return ts


def allowed_downtime(slo: float, window: timedelta) -> timedelta:
    if not 0 < slo < 1:
        raise ValueError("SLO là tỉ lệ trong (0, 1), ví dụ 0.999")
    return window * (1 - slo)


def merge_outages(spans: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for begin, finish in sorted(spans):
        if merged and begin <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], finish))
        else:
            merged.append((begin, finish))
    return merged


def downtime(incidents: list[dict], start: datetime, end: datetime) -> timedelta:
    if start >= end:
        raise ValueError("start phải trước end")
    spans = []
    for item in incidents:
        if item.get("impact") != "outage":
            continue
        begin = _parse(item["started_at"])
        if item.get("resolved_at"):
            finish = _parse(item["resolved_at"])
            if finish < begin:
                raise ValueError(f"Incident {item.get('id')} đóng trước khi mở")
        else:
            finish = end
        begin, finish = max(begin, start), min(finish, end)
        if begin < finish:
            spans.append((begin, finish))
    return sum((finish - begin for begin, finish in merge_outages(spans)), timedelta(0))


def availability(incidents: list[dict], start: datetime, end: datetime) -> float:
    return 1 - downtime(incidents, start, end) / (end - start)


def budget_remaining(slo: float, incidents: list[dict], start: datetime, end: datetime) -> timedelta:
    return allowed_downtime(slo, end - start) - downtime(incidents, start, end)
