"""Context engineering cho agent: cắt observation dài, rút gọn observation cũ, ép lịch sử vào ngân sách token."""

import math
from typing import Callable

MSG_OVERHEAD = 4


class ContextOverflowError(ValueError):
    pass


def approx_tokens(text: str) -> int:
    return math.ceil(len(text) / 3.5)


def messages_tokens(messages: list[dict], count: Callable[[str], int] = approx_tokens) -> int:
    return sum(count(m.get("content") or "") + MSG_OVERHEAD for m in messages)


def _marker(removed: int) -> str:
    return f"\n...[đã cắt {removed} ký tự]...\n"


def truncate_middle(text: str, max_tokens: int, count: Callable[[str], int] = approx_tokens) -> str:
    if count(text) <= max_tokens:
        return text
    if count(_marker(len(text))) > max_tokens:
        raise ContextOverflowError(f"max_tokens={max_tokens} không đủ chứa cả dấu cắt")
    lo, hi, best = 0, len(text) // 2, 0
    while lo <= hi:
        keep = (lo + hi) // 2
        removed = len(text) - 2 * keep
        if count(text[:keep] + _marker(removed) + text[len(text) - keep:]) <= max_tokens:
            best, lo = keep, keep + 1
        else:
            hi = keep - 1
    return text[:best] + _marker(len(text) - 2 * best) + text[len(text) - best:]


OBS_PREFIX = "Observation: "


def compact_history(messages: list[dict], keep_last: int = 2, stub_chars: int = 60) -> list[dict]:
    positions = [i for i, m in enumerate(messages)
                 if m.get("role") == "user" and (m.get("content") or "").startswith(OBS_PREFIX)]
    old = set(positions[:-keep_last] if keep_last > 0 else positions)
    out = []
    for i, m in enumerate(messages):
        m = dict(m)
        body = m["content"][len(OBS_PREFIX):] if i in old else ""
        if i in old and len(body) > stub_chars:
            m["content"] = f"{OBS_PREFIX}[đã rút gọn, {len(body)} ký tự] {body[:stub_chars]}..."
        out.append(m)
    return out


def dropped_note(n: int) -> dict:
    return {"role": "user", "content": f"[Đã lược bỏ {n} message cũ để vừa context.]"}


def fit_messages(messages: list[dict], budget: int, count: Callable[[str], int] = approx_tokens,
                 keep_last: int = 4) -> list[dict]:
    if messages_tokens(messages, count) <= budget:
        return [dict(m) for m in messages]
    head, rest = messages[:2], messages[2:]
    floor = min(keep_last, len(rest))
    for kept in range(len(rest) - 1, floor - 1, -1):
        candidate = [*head, dropped_note(len(rest) - kept), *(rest[len(rest) - kept:] if kept else [])]
        if messages_tokens(candidate, count) <= budget:
            return [dict(m) for m in candidate]
    raise ContextOverflowError(
        f"system + task + {floor} message cuối vẫn vượt ngân sách {budget} token: cắt observation trước")
