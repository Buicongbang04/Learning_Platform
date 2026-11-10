"""Context engineering cho agent: cắt observation dài, rút gọn observation cũ, ép lịch sử vào ngân sách token."""

import math
from typing import Callable

MSG_OVERHEAD = 4


class ContextOverflowError(ValueError):
    pass


def approx_tokens(text: str) -> int:
    """Ước lượng số token Qwen2.5 của văn bản tiếng Việt: khoảng 3.5 ký tự một token (module 11 đo 52 ký tự / 14.6 token)."""
    return math.ceil(len(text) / 3.5)


def messages_tokens(messages: list[dict], count: Callable[[str], int] = approx_tokens) -> int:
    """Tổng token của danh sách message: token của content cộng MSG_OVERHEAD cho mỗi message (thẻ vai của template)."""
    return sum(count(m.get("content") or "") + MSG_OVERHEAD for m in messages)


def _marker(removed: int) -> str:
    return f"\n...[đã cắt {removed} ký tự]...\n"


def truncate_middle(text: str, max_tokens: int, count: Callable[[str], int] = approx_tokens) -> str:
    """Cắt phần giữa của một observation dài, giữ đầu và đuôi.

    - count(text) <= max_tokens: trả nguyên văn.
    - Ngược lại trả text[:k] + _marker(len(text) - 2k) + text[-k:] (k ký tự đầu, k ký tự cuối, cùng k) với k LỚN NHẤT
      sao cho count(kết quả) <= max_tokens.
    - Không chứa nổi cả dấu cắt với k = 0: ContextOverflowError.
    """
    # TODO
    raise NotImplementedError


OBS_PREFIX = "Observation: "


def compact_history(messages: list[dict], keep_last: int = 2, stub_chars: int = 60) -> list[dict]:
    """Rút gọn observation cũ ("tool result clearing").

    Observation là message role "user" có content bắt đầu bằng OBS_PREFIX. Giữ nguyên `keep_last` observation cuối;
    mỗi observation cũ hơn có phần sau OBS_PREFIX (gọi là body) dài hơn stub_chars thì thay content bằng
    f"{OBS_PREFIX}[đã rút gọn, {len(body)} ký tự] {body[:stub_chars]}...". Message khác giữ nguyên. Trả list mới,
    không sửa list hay dict đầu vào.
    """
    # TODO
    raise NotImplementedError


def dropped_note(n: int) -> dict:
    return {"role": "user", "content": f"[Đã lược bỏ {n} message cũ để vừa context.]"}


def fit_messages(messages: list[dict], budget: int, count: Callable[[str], int] = approx_tokens,
                 keep_last: int = 4) -> list[dict]:
    """Ép lịch sử agent vào ngân sách token, KHÔNG BAO GIỜ bỏ system (messages[0]) và task (messages[1]).

    - Vừa ngân sách (messages_tokens <= budget): trả bản sao, không đổi gì.
    - Ngược lại: system, task, dropped_note(n), rồi đoạn đuôi liên tục DÀI NHẤT của messages[2:] sao cho tổng (tính cả
      ghi chú) vừa budget; n là số message bị bỏ.
    - Nếu giữ được ít hơn min(keep_last, len(messages) - 2) message cuối: ContextOverflowError.
    """
    # TODO
    raise NotImplementedError
