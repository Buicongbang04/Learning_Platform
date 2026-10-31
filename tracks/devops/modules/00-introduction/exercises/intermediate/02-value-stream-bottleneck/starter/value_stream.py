from datetime import datetime, timedelta

STAGES = {
    "coding": ("first_commit_at", "pr_opened_at"),
    "review_wait": ("pr_opened_at", "first_review_at"),
    "review": ("first_review_at", "approved_at"),
    "merge_wait": ("approved_at", "merged_at"),
    "deploy_wait": ("merged_at", "deployed_at"),
}


def parse_ts(value: str) -> datetime:
    # TODO: ISO 8601 có múi giờ, thiếu múi giờ thì ValueError
    raise NotImplementedError


def stage_durations(change: dict) -> dict[str, timedelta]:
    # TODO: thời gian của từng stage; PR tự merge (không review, không approve) thì review_wait và review bằng 0
    raise NotImplementedError


def completed_changes(changes: list[dict]) -> list[dict]:
    # TODO: chỉ các thay đổi đã deploy
    raise NotImplementedError


def unreviewed(changes: list[dict]) -> list[str]:
    # TODO
    raise NotImplementedError


def stage_medians(changes: list[dict]) -> dict[str, timedelta]:
    # TODO
    raise NotImplementedError


def bottleneck(changes: list[dict]) -> str | None:
    # TODO: stage có median lớn nhất, hoà thì lấy stage đứng trước
    raise NotImplementedError


def flow_efficiency(changes: list[dict], active: tuple[str, ...] = ("coding", "review")) -> float | None:
    # TODO: tổng thời gian active chia tổng lead time của mọi thay đổi đã deploy
    raise NotImplementedError
