import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(value)
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError(f"Thời điểm thiếu múi giờ: {value!r}")
    return ts.astimezone(timezone.utc)


def _check_window(start: datetime, end: datetime) -> None:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Cửa sổ phải có múi giờ")
    if start >= end:
        raise ValueError("start phải trước end")


def counted_deploys(deploys: list[dict], start: datetime, end: datetime) -> list[dict]:
    _check_window(start, end)
    counted = [
        d
        for d in deploys
        if d.get("env") == "production"
        and d.get("status") == "success"
        and not d.get("rollback_of")
        and start <= parse_ts(d["finished_at"]) < end
    ]
    return sorted(counted, key=lambda d: parse_ts(d["finished_at"]))


def _rolled_back(deploys: list[dict]) -> set[str]:
    return {d["rollback_of"] for d in deploys if d.get("rollback_of") and d.get("status") == "success"}


def failed_change_ids(deploys: list[dict], incidents: list[dict], start: datetime, end: datetime) -> set[str]:
    counted = {d["id"] for d in counted_deploys(deploys, start, end)}
    caused = {i["caused_by_deploy"] for i in incidents if i.get("caused_by_deploy")}
    return counted & (_rolled_back(deploys) | caused)


def deployment_frequency(deploys: list[dict], start: datetime, end: datetime) -> float:
    days = (end - start) / timedelta(days=1)
    return len(counted_deploys(deploys, start, end)) / days


def change_failure_rate(deploys: list[dict], incidents: list[dict], start: datetime, end: datetime) -> float | None:
    counted = counted_deploys(deploys, start, end)
    if not counted:
        return None
    return len(failed_change_ids(deploys, incidents, start, end)) / len(counted)


def lead_times(deploys: list[dict], commits: list[dict], start: datetime, end: datetime) -> dict[str, timedelta]:
    committed = {c["sha"]: parse_ts(c["committed_at"]) for c in commits}
    rolled_back = _rolled_back(deploys)
    result: dict[str, timedelta] = {}
    for deploy in counted_deploys(deploys, start, end):
        if deploy["id"] in rolled_back:
            continue
        shipped = parse_ts(deploy["finished_at"])
        for sha in deploy.get("commits") or []:
            if sha in committed and sha not in result:
                result[sha] = shipped - committed[sha]
    return result


def median_lead_time(deploys: list[dict], commits: list[dict], start: datetime, end: datetime) -> timedelta | None:
    values = list(lead_times(deploys, commits, start, end).values())
    return statistics.median(values) if values else None


def recovery_times(deploys: list[dict], incidents: list[dict], start: datetime, end: datetime) -> dict[str, timedelta]:
    by_id = {d["id"]: d for d in deploys}
    result: dict[str, timedelta] = {}
    for deploy_id in failed_change_ids(deploys, incidents, start, end):
        linked = [i for i in incidents if i.get("caused_by_deploy") == deploy_id]
        if any(not i.get("resolved_at") for i in linked):
            continue
        restored = [parse_ts(i["resolved_at"]) for i in linked]
        restored += [
            parse_ts(d["finished_at"])
            for d in deploys
            if d.get("rollback_of") == deploy_id and d.get("status") == "success"
        ]
        if restored:
            result[deploy_id] = max(restored) - parse_ts(by_id[deploy_id]["finished_at"])
    return result


def median_recovery_time(deploys: list[dict], incidents: list[dict], start: datetime, end: datetime) -> timedelta | None:
    values = list(recovery_times(deploys, incidents, start, end).values())
    return statistics.median(values) if values else None


def _hours(value: timedelta | None) -> float | None:
    return None if value is None else value / timedelta(hours=1)


def dora_report(deploys: list[dict], commits: list[dict], incidents: list[dict], start: datetime, end: datetime) -> dict:
    return {
        "deploys_per_week": deployment_frequency(deploys, start, end) * 7,
        "change_failure_rate": change_failure_rate(deploys, incidents, start, end),
        "median_lead_time_hours": _hours(median_lead_time(deploys, commits, start, end)),
        "median_recovery_hours": _hours(median_recovery_time(deploys, incidents, start, end)),
    }
