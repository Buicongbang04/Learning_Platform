"""Trích đáp số từ câu trả lời của LLM, so đáp số chính xác, và reward kiểm được cho GSM8K.

Chỉ dùng thư viện chuẩn trong tệp này (re, fractions).
"""

from __future__ import annotations

import re
from fractions import Fraction

_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_PLAIN = re.compile(r"[+-]?(?:\d+/\d+|\d+(?:\.\d+)?)")
NUMBER = re.compile(r"(?<![\w.])[-−]?\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?!\d)|(?<![\w.])[-−]?\$?(?:\d+/\d+|\d+(?:\.\d+)?)")
_ANSWER_TAG = re.compile(r"<answer>(.*?)</answer>", re.S)
_BOXED = re.compile(r"\\boxed\{((?:[^{}]|\{[^{}]*\})*)\}")
_HASHES = re.compile(r"####(.*)")
_PHRASE = re.compile(r"answer\s*(?:is|:)(.*)", re.I)
_LETTER = re.compile(r"[^\W\d_]")
_WORD = re.compile(r"[^\W_]")


def normalize_number(text: str) -> str | None:
    """Dạng chuẩn của một chuỗi chỉ chứa MỘT số, hoặc None nếu không phải đúng một số.

    Dạng chuẩn là str(Fraction(...)): "18", "-3", "5/2". Chấp nhận khoảng trắng hai đầu, dấu "$" và "%",
    dấu phẩy ngăn hàng nghìn ("1,234"), dấu chấm cuối câu ("18."), dấu "+" đầu, dấu trừ unicode "−",
    số thập phân ("2.50") và phân số ("3/4"). Mọi thứ khác (chữ, hai số, "1,2") cho None.
    """
    s = text.strip().replace("−", "-").replace("\\$", "").replace("$", "").replace("%", "").strip()
    s = _THOUSANDS.sub("", s)
    if s.endswith("."):
        s = s[:-1]
    if not _PLAIN.fullmatch(s):
        return None
    try:
        return str(Fraction(s))
    except ZeroDivisionError:
        return None


def gold_answer(answer_field: str) -> str:
    """Đáp số chuẩn hoá của cột `answer` GSM8K (phần sau "####")."""
    value = normalize_number(answer_field.split("####")[-1])
    if value is None:
        raise ValueError(f"không đọc được đáp số: {answer_field[-40:]!r}")
    return value


def _numbers(text: str) -> list[str]:
    found = (normalize_number(m.group(0)) for m in NUMBER.finditer(text))
    return [n for n in found if n is not None]


def extract_answer(completion: str) -> str | None:
    """Đáp số của một câu trả lời tự do, theo thứ tự ưu tiên ở README của bài."""
    for pattern, pick in ((_ANSWER_TAG, -1), (_BOXED, -1)):
        spans = pattern.findall(completion)
        if spans:
            numbers = _numbers(spans[-1])
            if numbers:
                return numbers[pick]
    for pattern in (_HASHES, _PHRASE):
        spans = pattern.findall(completion)
        if spans:
            numbers = _numbers(spans[-1])
            if numbers:
                return numbers[0]
    numbers = _numbers(completion)
    return numbers[-1] if numbers else None


def is_correct(completion: str, gold: str) -> bool:
    """extract_answer(completion) bằng đáp số gold (đã chuẩn hoá)."""
    return extract_answer(completion) == gold


def format_reward(completion: str) -> float:
    """1.0 nếu có lập luận rồi đúng một \\boxed{SỐ} ở cuối (sau đó không còn chữ hay số), ngược lại 0.0."""
    if completion.count("\\boxed{") != 1:
        return 0.0
    match = _BOXED.search(completion)
    if not match or normalize_number(match.group(1)) is None:
        return 0.0
    before, after = completion[:match.start()], completion[match.end():]
    return 1.0 if _LETTER.search(before) and not _WORD.search(after) else 0.0


def correctness_reward(completion: str, gold: str) -> float:
    """1.0 nếu \\boxed{} cuối cùng chứa đúng một số bằng gold, ngược lại 0.0."""
    spans = _BOXED.findall(completion)
    return 1.0 if spans and normalize_number(spans[-1]) == gold else 0.0


def total_reward(completion: str, gold: str, format_weight: float = 0.2) -> float:
    """correctness_reward + format_weight * format_reward."""
    return correctness_reward(completion, gold) + format_weight * format_reward(completion)
