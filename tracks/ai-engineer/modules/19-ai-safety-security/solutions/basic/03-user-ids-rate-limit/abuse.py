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
    if not secret:
        raise ValueError("cần secret không rỗng")
    canon = user_id.strip().casefold()
    if not canon:
        raise ValueError("user_id rỗng")
    return "u_" + hmac.new(secret, canon.encode("utf-8"), hashlib.sha256).hexdigest()[:24]


class TokenBucket:
    def __init__(self, rate_per_s: float, capacity: float, clock: Callable[[], float] = time.monotonic):
        if rate_per_s <= 0 or capacity <= 0:
            raise ValueError("rate và capacity phải dương")
        self.rate, self.capacity, self.clock = rate_per_s, capacity, clock
        self._state: dict[str, tuple[float, float]] = {}

    def _level(self, key: str) -> float:
        now = self.clock()
        tokens, last = self._state.get(key, (self.capacity, now))
        tokens = min(self.capacity, tokens + (now - last) * self.rate)
        self._state[key] = (tokens, now)
        return tokens

    def allow(self, key: str, cost: float = 1.0) -> bool:
        tokens = self._level(key)
        if cost > tokens:
            return False
        self._state[key] = (tokens - cost, self._state[key][1])
        return True

    def retry_after(self, key: str, cost: float = 1.0) -> float:
        if cost > self.capacity:
            return float("inf")
        return max(0.0, (cost - self._level(key)) / self.rate)


class AbuseTracker:
    def __init__(self, strikes: int, window_s: float, ban_s: float, clock: Callable[[], float] = time.monotonic):
        self.strikes, self.window_s, self.ban_s, self.clock = strikes, window_s, ban_s, clock
        self._events: dict[str, list[tuple[float, str]]] = {}
        self._bans: dict[str, int] = {}
        self._until: dict[str, float] = {}

    def record(self, key: str, reason: str) -> None:
        now = self.clock()
        events = [(t, r) for t, r in self._events.get(key, []) if now - t < self.window_s]
        events.append((now, reason))
        if len(events) >= self.strikes:
            n = self._bans.get(key, 0)
            self._until[key] = now + self.ban_s * 2**n
            self._bans[key] = n + 1
            events = []
        self._events[key] = events

    def banned(self, key: str) -> bool:
        return self.clock() < self._until.get(key, float("-inf"))

    def history(self, key: str) -> list[str]:
        now = self.clock()
        return [r for t, r in self._events.get(key, []) if now - t < self.window_s]


@dataclass
class Result:
    status: str
    reply: str | None = None
    flags: list[str] = field(default_factory=list)


def handle(user_id: str, text: str, *, secret: bytes, llm: Callable[[list[dict], str], str],
           moderate: Callable[[str], list[str]], limiter: TokenBucket, tracker: AbuseTracker,
           log: list[dict]) -> Result:
    key = user_key(user_id, secret)

    def done(result: Result) -> Result:
        log.append({"user": key, "status": result.status, "flags": list(result.flags)})
        return result

    if tracker.banned(key):
        return done(Result("banned", REFUSAL))
    if not limiter.allow(key):
        return done(Result("rate_limited", REFUSAL))
    flags = moderate(text)
    if flags:
        tracker.record(key, "input:" + ",".join(flags))
        return done(Result("blocked_input", REFUSAL, flags))
    reply = llm([{"role": "user", "content": text}], key)
    flags = moderate(reply)
    if flags:
        tracker.record(key, "output:" + ",".join(flags))
        return done(Result("blocked_output", REFUSAL, flags))
    return done(Result("ok", reply))
