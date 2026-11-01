"""M04: đọc đánh đổi giữa các mức quantize (module 10, bài Advanced 02)."""

from __future__ import annotations


def bits_per_weight(file_bytes: int, n_params: int) -> float:
    """Số bit trung bình mỗi tham số của một tệp model (GGUF gồm cả scale, zero-point, lớp giữ độ chính xác cao).

    `n_params <= 0`: `ValueError`.
    """
    raise NotImplementedError("M04: bits_per_weight")


def pareto_front(rows: list[dict], objectives: dict[str, str]) -> list[int]:
    """Chỉ số các dòng không bị dòng nào khác **trội hơn** (Pareto front), giữ thứ tự `rows`.

    `objectives`: tên cột → `"min"` hoặc `"max"`. Dòng A trội hơn B khi A không tệ hơn B ở mọi cột và tốt hơn hẳn ở
    ít nhất một cột. Hướng khác `"min"`/`"max"`: `ValueError`.
    """
    raise NotImplementedError("M04: pareto_front")
