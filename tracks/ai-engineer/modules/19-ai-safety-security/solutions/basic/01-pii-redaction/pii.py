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
    if not digits.isdigit() or not digits:
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def cccd_ok(digits: str) -> bool:
    return (
        len(digits) == 12
        and digits.isdigit()
        and digits[:3] in PROVINCE_CODES
        and digits[3] in "0123"
    )


_D = r"(?<![\d.,])"
_E = r"(?![\d]|[.,]\d)"
_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])")
_PHONE = re.compile(_D + r"(?:\+84|84|0)[\s.-]?[35789]\d(?:[\s.-]?\d){7}" + _E)
_CARD = re.compile(_D + r"\d{4}(?:[ -]?\d{4}){2}[ -]?\d{1,7}" + _E)
_TWELVE = re.compile(_D + r"\d{12}" + _E)
_KEYED = re.compile(
    r"(?P<key>\b(?:số tài khoản|stk|tài khoản số|tk số|số tk|cmnd|chứng minh nhân dân|số chứng minh)\b)"
    r"[\s:.#\-]*(?:là\s+|số\s+)?(?P<num>\d(?:[\s.-]?\d){5,18})" + _E,
    re.IGNORECASE,
)
_ADDRESS = re.compile(
    r"(?<!\w)(?:số\s+)?\d+[A-Za-z]?(?:/\d+[A-Za-z]?)*\s+(?:đường|phố|ngõ|hẻm|ngách)\s+[^,\n]+"
    r"(?:,\s*(?:phường|xã|thị trấn|quận|huyện|thị xã|tp\.?|thành phố|tỉnh)\s+[^,\n.]+)+",
    re.IGNORECASE,
)


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def find_pii(text: str) -> list[Span]:
    spans: list[Span] = []

    def add(start: int, end: int, kind: str) -> None:
        spans.append(Span(start, end, kind, text[start:end]))

    for m in _EMAIL.finditer(text):
        add(m.start(), m.end(), "EMAIL")
    for m in _PHONE.finditer(text):
        add(m.start(), m.end(), "PHONE")
    for m in _CARD.finditer(text):
        d = _digits(m.group())
        if 13 <= len(d) <= 19 and luhn_ok(d):
            add(m.start(), m.end(), "CARD")
    for m in _TWELVE.finditer(text):
        if cccd_ok(m.group()):
            add(m.start(), m.end(), "CCCD")
    for m in _KEYED.finditer(text):
        key = m.group("key").lower()
        d = _digits(m.group("num"))
        if "cmnd" in key or "chứng minh" in key:
            if len(d) == 9:
                add(m.start("num"), m.end("num"), "CMND")
        elif 6 <= len(d) <= 19:
            add(m.start("num"), m.end("num"), "BANK")
    for m in _ADDRESS.finditer(text):
        add(m.start(), m.end(), "ADDRESS")
    return resolve_overlaps(spans)


def resolve_overlaps(spans: list[Span]) -> list[Span]:
    order = sorted(spans, key=lambda s: (-(s.end - s.start), KINDS.index(s.kind), s.start))
    kept: list[Span] = []
    for s in order:
        if all(s.end <= k.start or s.start >= k.end for k in kept):
            kept.append(s)
    return sorted(kept, key=lambda s: s.start)


def redact(text: str, spans: list[Span] | None = None) -> str:
    spans = find_pii(text) if spans is None else resolve_overlaps(spans)
    out = text
    for s in sorted(spans, key=lambda s: s.start, reverse=True):
        out = out[: s.start] + f"[{s.kind}]" + out[s.end :]
    return out


_TOKEN = re.compile(r"<(?:" + "|".join(KINDS) + r")_[0-9a-f]{10}>")


class Pseudonymizer:
    """Thay mỗi giá trị PII bằng token `<KIND_xxxxxxxxxx>` (HMAC-SHA256 theo khoá), giữ bảng để khôi phục."""

    def __init__(self, key: bytes):
        if not key:
            raise ValueError("cần khoá bí mật không rỗng")
        self._key = key
        self.vault: dict[str, str] = {}

    def token(self, kind: str, value: str) -> str:
        if kind == "PHONE":
            canon = "0" + _digits(value)[-9:]
        elif kind in ("EMAIL", "ADDRESS"):
            canon = value.strip().lower()
        else:
            canon = _digits(value)
        digest = hmac.new(self._key, f"{kind}:{canon}".encode(), hashlib.sha256).hexdigest()[:10]
        tok = f"<{kind}_{digest}>"
        self.vault.setdefault(tok, value)
        return tok

    def pseudonymize(self, text: str) -> str:
        out = text
        for s in sorted(find_pii(text), key=lambda s: s.start, reverse=True):
            out = out[: s.start] + self.token(s.kind, s.text) + out[s.end :]
        return out

    def restore(self, text: str) -> str:
        return _TOKEN.sub(lambda m: self.vault.get(m.group(), m.group()), text)


def score(pred: list[Span], gold: list[Span]) -> dict[str, dict[str, float]]:
    out = {}
    for kind in sorted({s.kind for s in pred} | {s.kind for s in gold}):
        p = {(s.start, s.end) for s in pred if s.kind == kind}
        g = {(s.start, s.end) for s in gold if s.kind == kind}
        tp = len(p & g)
        out[kind] = dict(tp=tp, fp=len(p - g), fn=len(g - p),
                         precision=tp / len(p) if p else 1.0, recall=tp / len(g) if g else 1.0)
    return out
