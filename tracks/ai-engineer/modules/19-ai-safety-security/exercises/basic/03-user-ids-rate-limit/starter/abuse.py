"""End-user ID, rate limit theo người dùng, theo dõi lạm dụng và một pipeline moderation quanh lời gọi LLM.

Chỉ dùng thư viện chuẩn. Đồng hồ (`clock`) được truyền vào để test điều khiển thời gian.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from typing import Callable

REFUSAL = "Xin lỗi, tôi không thể hỗ trợ yêu cầu này."


def user_key(user_id: str, secret: bytes) -> str:
    """"u_" + 24 ký tự hex đầu của HMAC-SHA256(secret, user_id đã strip và casefold)."""
    # TODO
    raise NotImplementedError


class TokenBucket:
    """Mỗi `key` một bucket, bắt đầu đầy `capacity` token, nạp lại `rate_per_s` token mỗi giây."""

    def __init__(self, rate_per_s: float, capacity: float, clock: Callable[[], float] = time.monotonic):
        # TODO
        raise NotImplementedError

    def allow(self, key: str, cost: float = 1.0) -> bool:
        # TODO
        raise NotImplementedError

    def retry_after(self, key: str, cost: float = 1.0) -> float:
        # TODO
        raise NotImplementedError


class AbuseTracker:
    """Đủ `strikes` lần vi phạm trong `window_s` giây thì cấm `ban_s * 2**(số lần đã bị cấm trước đó)` giây."""

    def __init__(self, strikes: int, window_s: float, ban_s: float, clock: Callable[[], float] = time.monotonic):
        # TODO
        raise NotImplementedError

    def record(self, key: str, reason: str) -> None:
        # TODO
        raise NotImplementedError

    def banned(self, key: str) -> bool:
        # TODO
        raise NotImplementedError

    def history(self, key: str) -> list[str]:
        # TODO
        raise NotImplementedError


@dataclass
class Result:
    status: str
    reply: str | None = None
    flags: list[str] = field(default_factory=list)


def handle(user_id: str, text: str, *, secret: bytes, llm: Callable[[list[dict], str], str],
           moderate: Callable[[str], list[str]], limiter: TokenBucket, tracker: AbuseTracker,
           log: list[dict]) -> Result:
    """Cấm -> rate limit -> moderation input -> LLM -> moderation output; mỗi request ghi một dòng log."""
    # TODO
    raise NotImplementedError
