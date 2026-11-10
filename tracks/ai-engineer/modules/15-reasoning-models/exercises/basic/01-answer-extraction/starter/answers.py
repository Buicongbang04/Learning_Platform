"""Trích đáp số từ câu trả lời của LLM, so đáp số chính xác, và reward kiểm được cho GSM8K.

Chỉ dùng thư viện chuẩn trong tệp này (re, fractions).
"""

from __future__ import annotations

import re
from fractions import Fraction


def normalize_number(text: str) -> str | None:
    """Dạng chuẩn của một chuỗi chỉ chứa MỘT số, hoặc None nếu không phải đúng một số.

    Dạng chuẩn là str(Fraction(...)): "18", "-3", "5/2". Chấp nhận khoảng trắng hai đầu, dấu "$" và "%",
    dấu phẩy ngăn hàng nghìn ("1,234"), dấu chấm cuối câu ("18."), dấu "+" đầu, dấu trừ unicode "−",
    số thập phân ("2.50") và phân số ("3/4"). Mọi thứ khác (chữ, hai số, "1,2") cho None.
    """
    # TODO
    raise NotImplementedError


def gold_answer(answer_field: str) -> str:
    """Đáp số chuẩn hoá của cột `answer` GSM8K (phần sau "####")."""
    # TODO
    raise NotImplementedError


def extract_answer(completion: str) -> str | None:
    """Đáp số của một câu trả lời tự do, theo thứ tự ưu tiên ở README của bài."""
    # TODO
    raise NotImplementedError


def is_correct(completion: str, gold: str) -> bool:
    """extract_answer(completion) bằng đáp số gold (đã chuẩn hoá)."""
    # TODO
    raise NotImplementedError


def format_reward(completion: str) -> float:
    """1.0 nếu có lập luận rồi đúng một \\boxed{SỐ} ở cuối (sau đó không còn chữ hay số), ngược lại 0.0."""
    # TODO
    raise NotImplementedError


def correctness_reward(completion: str, gold: str) -> float:
    """1.0 nếu \\boxed{} cuối cùng chứa đúng một số bằng gold, ngược lại 0.0."""
    # TODO
    raise NotImplementedError


def total_reward(completion: str, gold: str, format_weight: float = 0.2) -> float:
    """correctness_reward + format_weight * format_reward."""
    # TODO
    raise NotImplementedError
