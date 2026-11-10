"""Guardrail tự viết cho input và output của một ứng dụng LLM: chuẩn hoá chống lách, danh sách chặn,
giới hạn độ dài, lọc link theo allowlist, kiểm lời gọi tool theo chính sách.

Chỉ dùng thư viện chuẩn. Quy tắc đầy đủ ở README của bài.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlsplit

CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s",
    "А": "a", "В": "b", "Е": "e", "К": "k", "М": "m", "Н": "h", "О": "o", "Р": "p", "С": "c", "Т": "t", "Х": "x",
    "ο": "o", "α": "a", "ι": "i", "ν": "v", "Ι": "i", "Ο": "o",
})


def normalize(text: str) -> str:
    """NFKC, bỏ ký tự định dạng vô hình, casefold, đổi chữ giống Latin, bỏ dấu tiếng Việt, mọi thứ không phải
    a-z0-9 thành một dấu cách."""
    # TODO
    raise NotImplementedError


def find_denied(text: str, phrases: list[str]) -> list[str]:
    """Các cụm trong `phrases` (theo thứ tự của `phrases`) xuất hiện trong `text` sau chuẩn hoá."""
    # TODO
    raise NotImplementedError


@dataclass
class Verdict:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


def check_input(text: str, *, max_chars: int, deny: list[str]) -> Verdict:
    """Lý do theo thứ tự: "empty", "too_long", rồi "denied:<cụm>" cho mỗi cụm bị chặn."""
    # TODO
    raise NotImplementedError


def host_allowed(url: str, allowed: set[str]) -> bool:
    """Host của URL là một tên miền trong `allowed` hoặc tên miền con của nó; URL có `\\`, khoảng trắng, ký tự
    điều khiển hay vô hình thì False."""
    # TODO
    raise NotImplementedError


def sanitize_links(reply: str, allowed: set[str]) -> tuple[str, list[str]]:
    """Xoá link tới host ngoài allowlist; trả (câu trả lời đã lọc, danh sách URL đã xoá theo thứ tự gặp)."""
    # TODO
    raise NotImplementedError


def check_tool_call(call: dict, policy: dict) -> list[str]:
    """Danh sách lỗi của lời gọi `{"name": ..., "arguments": {...}}` so với chính sách; rỗng là hợp lệ."""
    # TODO
    raise NotImplementedError
