"""PII scanner bằng regex + checksum."""

from __future__ import annotations

import re

import pandas as pd

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# TODO: viết thêm CARD_RE, CPF_RE, PHONE_RE

TYPES_IN_PRIORITY = ["email", "card", "cpf", "phone"]


def luhn_ok(number: str) -> bool:
    # TODO
    raise NotImplementedError


def cpf_ok(cpf: str) -> bool:
    # TODO: 11 chữ số, không phải toàn số giống nhau, 2 số kiểm tra đúng
    raise NotImplementedError


def detect(text: str) -> list[dict]:
    """Trả list {'type','value','start','end'} sắp theo start, không chồng lấn."""
    # TODO
    raise NotImplementedError


def redact(text: str) -> str:
    # TODO: thay mỗi match bằng [EMAIL], [CARD], [CPF], [PHONE]
    raise NotImplementedError


def scan_dataframe(df: pd.DataFrame, sample_size: int = 1000, threshold: float = 0.3) -> dict[str, set[str]]:
    # TODO
    raise NotImplementedError
