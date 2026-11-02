"""WER và CER cho tiếng Việt: chuẩn hoá, đếm S/D/I bằng quy hoạch động, tổng hợp mức corpus.

Chỉ dùng thư viện chuẩn trong tệp này (không dùng jiwer: test dùng nó để đối chiếu).
"""

from __future__ import annotations

import unicodedata


def normalize_vi(text: str) -> str:
    """NFC, chữ thường, thay dấu câu và ký hiệu bằng khoảng trắng (giữ dấu thanh), gộp khoảng trắng."""
    # TODO
    raise NotImplementedError


def edit_counts(ref: list[str], hyp: list[str]) -> dict[str, int]:
    """{"S", "D", "I", "N"} của một alignment có tổng S + D + I nhỏ nhất; N = len(ref)."""
    # TODO
    raise NotImplementedError


def wer(refs: list[str], hyps: list[str]) -> float:
    """WER mức corpus: tổng S + D + I trên mọi câu chia tổng số từ tham chiếu (sau normalize_vi)."""
    # TODO
    raise NotImplementedError


def cer(refs: list[str], hyps: list[str]) -> float:
    """CER mức corpus trên ký tự của chuỗi đã normalize_vi, tính cả khoảng trắng."""
    # TODO
    raise NotImplementedError
