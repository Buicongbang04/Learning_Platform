from pathlib import Path

FIELDS = ("workload", "team", "env", "replicas", "hours", "cpu_request_m", "mem_request_mi", "cpu_p95_m", "mem_max_mi")
NUMBERS = FIELDS[3:]
UNALLOCATED = "unallocated"


def load_usage(path: Path) -> list[dict]:
    # TODO: đọc CSV, kiểm cột, đổi số sang int, team rỗng thành None; số âm là ValueError
    raise NotImplementedError


def load_pricing(path: Path) -> dict:
    # TODO: đọc YAML; thiếu hay sai vcpu_hour, gib_hour, orders là ValueError
    raise NotImplementedError


def cost(row: dict, pricing: dict, cpu_m: int | None = None, mem_mi: int | None = None) -> float:
    # TODO: chi phí tháng theo request (hoặc theo cpu_m, mem_mi nếu truyền vào)
    raise NotImplementedError


def rightsize(row: dict, headroom: float = 0.2) -> dict:
    # TODO: {"cpu_m", "mem_mi", "action"} theo luật trong đề bài
    raise NotImplementedError


def allocate(rows: list[dict], pricing: dict) -> dict[str, float]:
    # TODO: chi phí trực tiếp theo team cộng phần chi phí chung chia theo tỉ lệ
    raise NotImplementedError


def savings(rows: list[dict], pricing: dict) -> float:
    # TODO: chi phí tháng tiết kiệm được khi áp mọi đề xuất rightsize
    raise NotImplementedError


def idle(rows: list[dict], cpu_ratio: float = 0.05, mem_ratio: float = 0.2) -> list[tuple[str, str]]:
    # TODO: (workload, env) gần như không dùng gì
    raise NotImplementedError


def unit_cost(rows: list[dict], pricing: dict) -> float:
    # TODO: tổng chi phí tháng chia cho mỗi 1000 đơn hàng
    raise NotImplementedError
