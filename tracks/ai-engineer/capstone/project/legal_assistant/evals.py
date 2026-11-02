"""M08: số liệu vận hành và cổng hồi quy cho eval suite (module 20)."""

from __future__ import annotations


def latency_summary(seconds: list[float]) -> dict[str, float]:
    """`{"n", "mean", "p50", "p95"}` với phân vị nội suy tuyến tính (mặc định của `numpy.percentile`).

    Danh sách rỗng: `ValueError`.
    """
    raise NotImplementedError("M08: latency_summary")


def percentile_ci(seconds: list[float], q: float, n_boot: int = 1000, seed: int = 0, level: float = 0.95) -> tuple[float, float]:
    """Khoảng tin cậy bootstrap cho phân vị `q` (0..100): lấy mẫu có hoàn lại `n_boot` lần cùng cỡ, tính phân vị mỗi
    lần, trả phân vị `(1 - level) / 2` và `(1 + level) / 2` của các giá trị đó. Cùng `seed` cho cùng kết quả.
    """
    raise NotImplementedError("M08: percentile_ci")


def cost_per_query(prompt_tokens: float, completion_tokens: float, usd_in_per_mtok: float, usd_out_per_mtok: float) -> float:
    """Chi phí USD của một câu hỏi theo giá mỗi triệu token vào/ra."""
    raise NotImplementedError("M08: cost_per_query")


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    """Cohen's kappa giữa hai người chấm nhãn nhị phân (ví dụ judge và nhãn người, module 20 mục 2):
    `(p_o - p_e) / (1 - p_e)`. Khác độ dài hoặc rỗng: `ValueError`. `p_e = 1` (cả hai luôn cùng một nhãn): `nan`.
    """
    raise NotImplementedError("M08: cohen_kappa")


def regression_gate(current: dict[str, float], baseline: dict[str, float], rules: dict[str, tuple[str, float]]) -> list[str]:
    """Cổng chặn merge khi chất lượng tụt. `rules`: tên số đo → `(hướng, dung sai)` với hướng `"higher"` (càng cao
    càng tốt) hoặc `"lower"`. Một số đo **hỏng** khi tệ đi hơn dung sai so với baseline. Trả danh sách mô tả các số đo
    hỏng (thiếu số đo ở một bên cũng là hỏng); rỗng nghĩa là qua cổng. Hướng không hợp lệ: `ValueError`.
    """
    raise NotImplementedError("M08: regression_gate")
