"""Phát hiện, che và giả danh hoá (pseudonymize) PII tiếng Việt bằng regex + kiểm tra cấu trúc.

Chỉ dùng thư viện chuẩn. Quy tắc đầy đủ của từng loại ở README của bài.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass

PROVINCE_CODES = frozenset(
    "001 002 004 006 008 010 011 012 014 015 017 019 020 022 024 025 026 027 030 031 033 034 035 036 037 038 040 "
    "042 044 045 046 048 049 051 052 054 056 058 060 062 064 066 067 068 070 072 074 075 077 079 080 082 083 084 "
    "086 087 089 091 092 093 094 095 096".split()
)
KINDS = ("BANK", "CMND", "CARD", "CCCD", "PHONE", "EMAIL", "ADDRESS")


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    kind: str
    text: str


def luhn_ok(digits: str) -> bool:
    """Chuỗi chữ số qua kiểm tra Luhn (số thẻ thanh toán). Chuỗi rỗng hoặc có ký tự khác số: False."""
    # TODO
    raise NotImplementedError


def cccd_ok(digits: str) -> bool:
    """12 chữ số, 3 số đầu là mã tỉnh trong PROVINCE_CODES, số thứ 4 (thế kỷ + giới tính) trong 0..3."""
    # TODO
    raise NotImplementedError


def find_pii(text: str) -> list[Span]:
    """Mọi span PII trong text (CARD, CCCD, BANK, PHONE, CMND, EMAIL, ADDRESS), không chồng lấn, theo vị trí."""
    # TODO
    raise NotImplementedError


def resolve_overlaps(spans: list[Span]) -> list[Span]:
    """Giữ span dài hơn khi chồng lấn; dài bằng nhau thì theo thứ tự KINDS. Trả theo `start` tăng dần."""
    # TODO
    raise NotImplementedError


def redact(text: str, spans: list[Span] | None = None) -> str:
    """Thay mỗi span bằng `[KIND]`. `spans=None` thì dùng find_pii; spans truyền vào cũng phải qua resolve_overlaps."""
    # TODO
    raise NotImplementedError


class Pseudonymizer:
    """Thay mỗi giá trị PII bằng token `<KIND_xxxxxxxxxx>` (10 ký tự hex của HMAC-SHA256 theo khoá),
    giữ bảng `vault` token -> giá trị gốc để khôi phục."""

    def __init__(self, key: bytes):
        # TODO
        raise NotImplementedError

    def token(self, kind: str, value: str) -> str:
        # TODO
        raise NotImplementedError

    def pseudonymize(self, text: str) -> str:
        # TODO
        raise NotImplementedError

    def restore(self, text: str) -> str:
        # TODO
        raise NotImplementedError


def score(pred: list[Span], gold: list[Span]) -> dict[str, dict[str, float]]:
    """Theo từng loại: tp, fp, fn, precision, recall; một span đúng khi trùng cả (start, end) và loại."""
    # TODO
    raise NotImplementedError
