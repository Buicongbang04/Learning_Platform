"""Cost attribution cho nền tảng ML: chi phí trực tiếp theo đội và model, chi phí idle, showback, chargeback."""

from pathlib import Path

RESOURCES = {"cpu_hours": "cpu_hour", "gpu_hours": "gpu_hour", "mem_gb_hours": "mem_gb_hour"}
UNALLOCATED = "unallocated"
UNLABELLED = "unlabelled"


def load_usage(path: Path) -> list[dict]:
    # TODO 1: đọc CSV, ép kiểu số, model rỗng thành None
    raise NotImplementedError


def row_cost(row: dict, prices: dict) -> float:
    # TODO 2
    raise NotImplementedError


def cost_by_model(rows: list[dict], config: dict) -> dict[tuple[str, str], float]:
    # TODO 3: {(team, model): chi phí trực tiếp}
    raise NotImplementedError


def idle_cost(rows: list[dict], config: dict) -> float:
    # TODO 4: phần năng lực đã cấp mà không ai dùng, tính theo từng loại tài nguyên
    raise NotImplementedError


def showback(rows: list[dict], config: dict) -> dict[str, dict[str, float]]:
    # TODO 5: {team: {"direct", "idle_share", "total"}}
    raise NotImplementedError


def chargeback(rows: list[dict], config: dict) -> list[dict]:
    # TODO 6: [{"cost_center", "team", "amount"}] sắp theo cost_center
    raise NotImplementedError
