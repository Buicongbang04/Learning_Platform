"""Kiểm lại các con số trong một design doc: tính lại từng claim từ inputs và so với con số doc đưa ra."""

from __future__ import annotations

import math


def recompute(claim: dict) -> float:
    """Tính lại giá trị đúng của một claim từ `claim["kind"]` và `claim["inputs"]` (công thức ở README).

    Ném ValueError khi kind không biết hoặc thiếu input bắt buộc.
    """
    # TODO
    raise NotImplementedError


def check_claims(claims: list[dict], rel_tol: float = 0.1) -> list[dict]:
    """Mỗi claim một dict {"id", "claimed", "recomputed", "rel_error", "ok"}, cùng thứ tự đầu vào."""
    # TODO
    raise NotImplementedError
