"""Guardrail tự viết cho input và output của một ứng dụng LLM: chuẩn hoá chống lách, danh sách chặn,
giới hạn độ dài, lọc link theo allowlist, kiểm lời gọi tool theo chính sách.

Chỉ dùng thư viện chuẩn.
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
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    text = text.casefold().translate(CONFUSABLES)
    text = text.replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _phrase_pattern(phrase: str) -> re.Pattern:
    squashed = normalize(phrase).replace(" ", "")
    return re.compile(r"(?<![a-z0-9])" + " ?".join(map(re.escape, squashed)) + r"(?![a-z0-9])")


def find_denied(text: str, phrases: list[str]) -> list[str]:
    norm = normalize(text)
    return [p for p in phrases if normalize(p) and _phrase_pattern(p).search(norm)]


@dataclass
class Verdict:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


def check_input(text: str, *, max_chars: int, deny: list[str]) -> Verdict:
    reasons = []
    if not normalize(text):
        reasons.append("empty")
    if len(text) > max_chars:
        reasons.append("too_long")
    reasons += [f"denied:{p}" for p in find_denied(text, deny)]
    return Verdict(not reasons, reasons)


def host_allowed(url: str, allowed: set[str]) -> bool:
    if "\\" in url or any(ch.isspace() or unicodedata.category(ch) in ("Cc", "Cf") for ch in url):
        return False
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").lower()
    except ValueError:
        return False
    if parts.scheme.lower() not in ("http", "https"):
        return False
    return any(host == d or host.endswith("." + d) for d in allowed)


_MD = re.compile(r"!?\[([^\]]*)\]\(\s*(?:<([^>]*)>|([^)\s>]+))(?:\s+\"[^\"]*\")?\s*\)")
_AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
_BARE = re.compile(r"(?i)(?:https?://|www\.)[^\s<>()\"']+")


def sanitize_links(reply: str, allowed: set[str]) -> tuple[str, list[str]]:
    removed: list[str] = []

    def md(m):
        url = m.group(2) if m.group(2) is not None else m.group(3)
        if host_allowed(url if "://" in url else "http://" + url, allowed):
            return m.group(0)
        removed.append(url)
        return m.group(1) if not m.group(0).startswith("!") else ""

    def bare(m):
        url = m.group(1) if m.re is _AUTOLINK else m.group(0)
        if host_allowed(url if "://" in url else "http://" + url, allowed):
            return m.group(0)
        removed.append(url)
        return "[link đã bị xoá]"

    out = _MD.sub(md, reply)
    out = _AUTOLINK.sub(bare, out)
    out = _BARE.sub(bare, out)
    return out, removed


def check_tool_call(call: dict, policy: dict) -> list[str]:
    name = call.get("name")
    args = call.get("arguments")
    if name not in policy:
        return [f"tool not allowed: {name}"]
    if not isinstance(args, dict):
        return ["arguments must be an object"]
    rules = policy[name]
    errors = [f"unknown argument: {k}" for k in args if k not in rules]
    for arg, rule in rules.items():
        if arg not in args:
            errors.append(f"missing argument: {arg}")
            continue
        value = args[arg]
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"{arg}: not in allowed values")
        if "pattern" in rule and not (isinstance(value, str) and re.fullmatch(rule["pattern"], value)):
            errors.append(f"{arg}: does not match pattern")
        if "max" in rule and not (isinstance(value, (int, float)) and not isinstance(value, bool) and value <= rule["max"]):
            errors.append(f"{arg}: above max or not a number")
    return errors
