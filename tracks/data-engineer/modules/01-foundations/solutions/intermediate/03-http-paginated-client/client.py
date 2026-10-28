"""HTTP client cho API đơn hàng: timeout, retry có exponential backoff, phân trang theo cursor."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator
from typing import Any

import requests

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
DEFAULT_TIMEOUT = (3.05, 30)  # (connect, read) giây


def backoff_delay(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    """Thời gian chờ trước lần thử lại thứ `attempt` (0, 1, 2…): min(cap, base * 2**attempt)."""
    return min(cap, base * (2**attempt))


def _retry_after(resp: requests.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None  # dạng HTTP-date: bỏ qua, dùng backoff


def get_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any] | None = None,
    *,
    headers: dict[str, str] | None = None,
    max_retries: int = 3,
    base_delay: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """GET và trả JSON, thử lại tối đa `max_retries` lần với lỗi tạm thời."""
    for attempt in range(max_retries + 1):
        last_try = attempt == max_retries
        try:
            resp = session.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        except (requests.ConnectionError, requests.Timeout) as exc:
            if last_try:
                raise
            delay = backoff_delay(attempt, base_delay)
            logger.warning("Lỗi kết nối %s (%s), thử lại sau %.2fs", url, exc, delay)
            sleep(delay)
            continue

        if resp.status_code not in RETRYABLE_STATUS:
            resp.raise_for_status()  # 4xx khác: lỗi thật, không retry
            return resp.json()
        if last_try:
            resp.raise_for_status()

        delay = _retry_after(resp) if resp.status_code == 429 else None
        if delay is None:
            delay = backoff_delay(attempt, base_delay)
        logger.warning("HTTP %d từ %s, thử lại sau %.2fs", resp.status_code, url, delay)
        sleep(delay)

    raise AssertionError("không tới được đây")


def iter_orders(
    base_url: str,
    token: str,
    *,
    page_size: int = 100,
    session: requests.Session | None = None,
    max_retries: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[dict[str, Any]]:
    """Generator duyệt mọi đơn hàng qua GET {base_url}/orders?limit=..&cursor=.."""
    own_session = session is None
    session = session or requests.Session()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = base_url.rstrip("/") + "/orders"
    cursor: str | None = None
    try:
        while True:
            params: dict[str, Any] = {"limit": page_size}
            if cursor is not None:
                params["cursor"] = cursor
            page = get_json(session, url, params, headers=headers, max_retries=max_retries, sleep=sleep)
            yield from page.get("data", [])
            cursor = page.get("next_cursor")
            if not cursor:
                return
    finally:
        if own_session:
            session.close()
