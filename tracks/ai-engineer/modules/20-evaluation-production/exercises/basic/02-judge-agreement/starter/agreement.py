"""Đo độ khớp của LLM judge với nhãn người và thiên vị vị trí.

Đọc đề trong README của bài. Chỉ dùng thư viện chuẩn.
"""

from __future__ import annotations

import math
from collections import Counter

VERDICTS = ("first", "second", "tie")


def cohen_kappa(a, b) -> float:
    """Cohen's kappa giữa hai dãy nhãn cùng độ dài."""
    # TODO
    raise NotImplementedError


def calibration_report(judge, human) -> dict:
    """n, unparsed, accuracy, kappa, false_pass, false_fail, judge_pass_rate, human_pass_rate."""
    # TODO
    raise NotImplementedError


def resolve_swap(v_ab: str, v_ba: str) -> str:
    """Gộp verdict của hai thứ tự (A, B) và (B, A) thành "A", "B", "tie" hoặc "inconsistent"."""
    # TODO
    raise NotImplementedError


def pairwise_summary(pairs) -> dict:
    """n, A, B, tie, inconsistent, consistency, win_rate_A, first_rate."""
    # TODO
    raise NotImplementedError
