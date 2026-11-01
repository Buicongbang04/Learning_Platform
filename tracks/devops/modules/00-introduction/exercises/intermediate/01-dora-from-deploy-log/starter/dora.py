import json
from datetime import datetime, timedelta
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def parse_ts(value: str) -> datetime:
    # TODO: đọc ISO 8601 (có cả hậu tố Z), từ chối thời điểm không có múi giờ, trả datetime ở UTC
    raise NotImplementedError


def counted_deploys(deploys: list[dict], start: datetime, end: datetime) -> list[dict]:
    # TODO: deploy production, status success, không phải rollback, finished_at trong [start, end), sắp theo thời gian
    raise NotImplementedError


def failed_change_ids(deploys: list[dict], incidents: list[dict], start: datetime, end: datetime) -> set[str]:
    # TODO: deploy được đếm mà sau đó bị rollback hoặc gây ra incident
    raise NotImplementedError


def deployment_frequency(deploys: list[dict], start: datetime, end: datetime) -> float:
    # TODO: số deploy được đếm chia số ngày của cửa sổ
    raise NotImplementedError


def change_failure_rate(deploys: list[dict], incidents: list[dict], start: datetime, end: datetime) -> float | None:
    # TODO
    raise NotImplementedError


def lead_times(deploys: list[dict], commits: list[dict], start: datetime, end: datetime) -> dict[str, timedelta]:
    # TODO: sha -> thời gian từ commit tới deploy đầu tiên chứa nó mà không bị rollback
    raise NotImplementedError


def median_lead_time(deploys: list[dict], commits: list[dict], start: datetime, end: datetime) -> timedelta | None:
    # TODO
    raise NotImplementedError


def recovery_times(deploys: list[dict], incidents: list[dict], start: datetime, end: datetime) -> dict[str, timedelta]:
    # TODO: id deploy lỗi -> thời gian từ lúc deploy xong tới sự kiện khôi phục cuối cùng
    raise NotImplementedError


def median_recovery_time(deploys: list[dict], incidents: list[dict], start: datetime, end: datetime) -> timedelta | None:
    # TODO
    raise NotImplementedError


def dora_report(deploys: list[dict], commits: list[dict], incidents: list[dict], start: datetime, end: datetime) -> dict:
    # TODO: deploys_per_week, change_failure_rate, median_lead_time_hours, median_recovery_hours
    raise NotImplementedError
