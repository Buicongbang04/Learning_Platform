import math


def step_metrics(summary: dict, steps: list[int], step_seconds: float) -> list[dict]:
    # TODO: mỗi bước một dict rps, achieved_rps, p95_ms, avg_ms, error_rate; thiếu submetric là ValueError
    raise NotImplementedError


def knee(rows: list[dict], slo_p95_ms: float = 200, max_error_rate: float = 0.01, min_achieved: float = 0.9) -> int | None:
    # TODO: bước cao nhất mà nó và mọi bước thấp hơn đều khoẻ
    raise NotImplementedError


def littles_law(rps: float, avg_ms: float) -> float:
    # TODO: số request đang xử lý cùng lúc
    raise NotImplementedError


def replicas(peak_rps: float, knee_rps: float, headroom: float = 0.3, spare: int = 1) -> int:
    # TODO: số replica cho đỉnh, cộng headroom và replica dự phòng
    raise NotImplementedError


def report(summary: dict, steps: list[int], step_seconds: float, peak_rps: float, slo_p95_ms: float = 200) -> str:
    # TODO: bảng markdown và ba dòng kết luận như đề bài
    raise NotImplementedError
