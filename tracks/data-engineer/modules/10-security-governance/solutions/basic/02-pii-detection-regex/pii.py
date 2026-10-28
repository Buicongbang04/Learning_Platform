"""PII scanner bằng regex + checksum (lời giải)."""

from __future__ import annotations

import re

import pandas as pd

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
CPF_RE = re.compile(r"(?<!\d)(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})(?!\d)")
PHONE_RE = re.compile(r"(?<![\d+])(?:\+84[ .]?|0)[35789](?:[ .]?\d){8}(?!\d)")

PATTERNS = {"email": EMAIL_RE, "card": CARD_RE, "cpf": CPF_RE, "phone": PHONE_RE}
VALIDATORS = {"card": lambda v: luhn_ok(v), "cpf": lambda v: cpf_ok(v)}
TYPES_IN_PRIORITY = ["email", "card", "cpf", "phone"]
LABELS = {"email": "[EMAIL]", "card": "[CARD]", "cpf": "[CPF]", "phone": "[PHONE]"}


def _digits(s: str) -> list[int]:
    return [int(c) for c in s if c.isdigit()]


def luhn_ok(number: str) -> bool:
    digits = _digits(number)
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def cpf_ok(cpf: str) -> bool:
    d = _digits(cpf)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for n in (9, 10):
        s = sum(d[i] * (n + 1 - i) for i in range(n))
        r = (s * 10) % 11
        if r == 10:
            r = 0
        if r != d[n]:
            return False
    return True


def detect(text: str) -> list[dict]:
    """Trả list {'type','value','start','end'} sắp theo start, không chồng lấn."""
    found: list[dict] = []
    for kind in TYPES_IN_PRIORITY:
        validate = VALIDATORS.get(kind, lambda v: True)
        for m in PATTERNS[kind].finditer(text):
            s, e = m.span()
            if any(s < f["end"] and f["start"] < e for f in found):
                continue
            if validate(m.group()):
                found.append({"type": kind, "value": m.group(), "start": s, "end": e})
    return sorted(found, key=lambda f: f["start"])


def redact(text: str) -> str:
    out = text
    for f in sorted(detect(text), key=lambda f: f["start"], reverse=True):
        out = out[: f["start"]] + LABELS[f["type"]] + out[f["end"]:]
    return out


def scan_dataframe(df: pd.DataFrame, sample_size: int = 1000, threshold: float = 0.3) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            continue
        sample = series.dropna().astype(str).head(sample_size)
        if sample.empty:
            continue
        counts: dict[str, int] = {}
        for value in sample:
            for kind in {f["type"] for f in detect(value)}:
                counts[kind] = counts.get(kind, 0) + 1
        hits = {k for k, c in counts.items() if c / len(sample) >= threshold}
        if hits:
            result[col] = hits
    return result
