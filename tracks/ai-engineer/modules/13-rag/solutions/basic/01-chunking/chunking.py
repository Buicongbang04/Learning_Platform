"""Chuẩn hoá văn bản và chunking: cố định theo ký tự, và theo Khoản/Điểm của văn bản luật.

Chỉ dùng thư viện chuẩn trong tệp này.
"""

from __future__ import annotations

import re
import unicodedata

KHOAN = re.compile(r"\d+\.\s")  # "1. ", "12. " ở đầu dòng; "150.000 đồng" không khớp
DIEM = re.compile(r"[a-zđ]\)\s")  # "a) ", ..., "d) ", "đ) ", "e) " ở đầu dòng


def normalize(text: str) -> str:
    """NFC; trong mỗi dòng gộp mọi chuỗi khoảng trắng thành một dấu cách và bỏ ở hai đầu; bỏ dòng trống."""
    text = unicodedata.normalize("NFC", text)
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def chunk_fixed(text: str, size: int, overlap: int) -> list[str]:
    """Cắt theo ký tự: chunk dài `size`, chunk sau bắt đầu sau chunk trước `size - overlap` ký tự."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError(f"cần size > 0 và 0 <= overlap < size, nhận size={size}, overlap={overlap}")
    step = size - overlap
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        if start + size >= len(text):
            break
        start += step
    return chunks


def _split_at(lines: list[str], pattern: re.Pattern) -> tuple[list[str], list[list[str]]]:
    """Tách dãy dòng thành (các dòng trước dòng khớp đầu tiên, các nhóm bắt đầu bằng dòng khớp)."""
    lead: list[str] = []
    groups: list[list[str]] = []
    for line in lines:
        if pattern.match(line):
            groups.append([line])
        elif groups:
            groups[-1].append(line)
        else:
            lead.append(line)
    return lead, groups


def chunk_legal(article_text: str, max_chars: int) -> list[str]:
    """Chunk một Điều theo khoản; khoản dài hơn `max_chars` tách tiếp theo điểm.

    Dòng đầu là tiêu đề Điều, đứng đầu mọi chunk. Chunk theo điểm giữ thêm phần dẫn của khoản.
    """
    lines = normalize(article_text).split("\n")
    header, body = lines[0], lines[1:]
    if not body:
        return [header]
    preamble, khoans = _split_at(body, KHOAN)
    units = ([preamble] if preamble else []) + khoans

    chunks = []
    for unit in units:
        text = "\n".join(unit)
        lead, diems = _split_at(unit, DIEM)
        if len(text) <= max_chars or not diems:
            chunks.append(f"{header}\n{text}")
            continue
        prefix = "\n".join([header, *lead])
        chunks.extend(f"{prefix}\n" + "\n".join(diem) for diem in diems)
    return chunks
