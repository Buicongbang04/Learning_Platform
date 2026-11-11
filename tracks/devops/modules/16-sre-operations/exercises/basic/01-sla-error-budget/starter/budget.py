from pathlib import Path

FIELDS = ("hour", "requests", "errors", "slow", "maintenance")


def load(path: Path) -> list[dict]:
    # TODO: đọc CSV, kiểm đúng cột FIELDS, đổi số sang int và maintenance sang bool; errors + slow ngoài [0, requests] là ValueError
    raise NotImplementedError


def sli(rows: list[dict]) -> float:
    # TODO: tỉ lệ request tốt (không 5xx, không chậm) trên tổng request; không có request là ValueError
    raise NotImplementedError


def budget_report(rows: list[dict], slo: float) -> dict:
    # TODO: total, bad, allowed_bad, consumed, remaining, exhausted_at
    raise NotImplementedError


def burn_rates(rows: list[dict], slo: float, end_hour: str, windows=(1, 6, 24, 72)) -> dict[int, float]:
    # TODO: burn rate của từng cửa sổ (số giờ) kết thúc ở end_hour, tính cả giờ end_hour
    raise NotImplementedError


def sla_availability(rows: list[dict], threshold: float = 0.05) -> float:
    # TODO: tỉ lệ giờ không sập theo hợp đồng, bỏ giờ bảo trì đã báo trước
    raise NotImplementedError


def sla_credit(availability: float, tiers) -> int:
    # TODO: phần trăm credit theo bảng tiers [(mức % tối thiểu, credit %), ...]
    raise NotImplementedError


def policy(report: dict) -> str:
    # TODO: "normal", "caution" hoặc "freeze" theo phần budget còn lại
    raise NotImplementedError
