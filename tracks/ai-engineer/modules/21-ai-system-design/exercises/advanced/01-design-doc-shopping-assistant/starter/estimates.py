"""Ước lượng cho design doc: từ assumptions.yaml ra bảng số trong mục 3 của DESIGN.md.

Định nghĩa từng chỉ số ở README bài (mục "Đề bài"). Dùng lại công thức bạn đã viết ở các bài Basic
và Intermediate của module (chép vào đây; bài này phải tự chạy được một mình).
"""

from __future__ import annotations

import math

GiB = 1024**3
HOURS_PER_MONTH = 730
# Thứ tự dòng trong bảng của render_table
ORDER = [
    "requests_per_day",
    "peak_rps",
    "peak_concurrency",
    "api_cost_per_request",
    "api_cost_per_1k",
    "api_monthly_usd",
    "weights_gib",
    "kv_kib_per_token",
    "seqs_per_gpu",
    "gpus_for_memory",
    "gpus_for_throughput",
    "gpus",
    "self_host_monthly_usd",
]


def estimate(assumptions: dict) -> dict:
    """Trả dict đúng các khoá trong ORDER. Ném ValueError khi cached > input hoặc model không vừa GPU."""
    # TODO
    raise NotImplementedError


def render_table(est: dict) -> str:
    """Bảng markdown hai cột `| Chỉ số | Giá trị |`, mỗi khoá của ORDER một dòng, định dạng như README."""
    # TODO
    raise NotImplementedError
