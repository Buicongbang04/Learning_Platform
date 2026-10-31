import statistics
from datetime import datetime, timedelta

STAGES = {
    "coding": ("first_commit_at", "pr_opened_at"),
    "review_wait": ("pr_opened_at", "first_review_at"),
    "review": ("first_review_at", "approved_at"),
    "merge_wait": ("approved_at", "merged_at"),
    "deploy_wait": ("merged_at", "deployed_at"),
}


def parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(value)
    if ts.utcoffset() is None:
        raise ValueError(f"Thời điểm thiếu múi giờ: {value!r}")
    return ts


def _is_self_merged(change: dict) -> bool:
    return not change.get("first_review_at") and not change.get("approved_at")


def stage_durations(change: dict) -> dict[str, timedelta]:
    if not change.get("deployed_at"):
        raise ValueError(f"{change.get('id')} chưa deploy")
    if bool(change.get("first_review_at")) != bool(change.get("approved_at")):
        raise ValueError(f"{change.get('id')} có review nhưng thiếu approve (hoặc ngược lại)")
    stamps = dict(change)
    if _is_self_merged(change):
        stamps["first_review_at"] = stamps["approved_at"] = change["pr_opened_at"]
    result = {}
    for stage, (begin, finish) in STAGES.items():
        duration = parse_ts(stamps[finish]) - parse_ts(stamps[begin])
        if duration < timedelta(0):
            raise ValueError(f"{change.get('id')}: {finish} trước {begin}")
        result[stage] = duration
    return result


def completed_changes(changes: list[dict]) -> list[dict]:
    return [c for c in changes if c.get("deployed_at")]


def unreviewed(changes: list[dict]) -> list[str]:
    return [c["id"] for c in changes if c.get("merged_at") and _is_self_merged(c)]


def stage_medians(changes: list[dict]) -> dict[str, timedelta]:
    rows = [stage_durations(c) for c in completed_changes(changes)]
    if not rows:
        return {}
    return {stage: statistics.median(r[stage] for r in rows) for stage in STAGES}


def bottleneck(changes: list[dict]) -> str | None:
    medians = stage_medians(changes)
    if not medians:
        return None
    return max(STAGES, key=lambda stage: (medians[stage], -list(STAGES).index(stage)))


def flow_efficiency(changes: list[dict], active: tuple[str, ...] = ("coding", "review")) -> float | None:
    rows = [stage_durations(c) for c in completed_changes(changes)]
    total = sum((d for r in rows for d in r.values()), timedelta(0))
    if not total:
        return None
    return sum((r[stage] for r in rows for stage in active), timedelta(0)) / total
