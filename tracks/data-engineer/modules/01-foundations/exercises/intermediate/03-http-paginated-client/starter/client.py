"""HTTP client cho API đơn hàng: timeout, retry có exponential backoff, phân trang theo cursor."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import Any

import requests

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
DEFAULT_TIMEOUT = (3.05, 30)  # (connect, read) giây


def backoff_delay(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    """Thời gian chờ trước lần thử lại thứ `attempt` (0, 1, 2…): min(cap, base * 2**attempt)."""
    # TODO 1
    raise NotImplementedError


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
    """GET và trả JSON, thử lại tối đa `max_retries` lần với lỗi tạm thời.

    - Luôn truyền timeout=DEFAULT_TIMEOUT.
    - Retry khi: status thuộc RETRYABLE_STATUS, requests.ConnectionError, requests.Timeout.
    - 429 có header Retry-After (số giây) thì chờ đúng số giây đó, ngược lại chờ backoff_delay.
    - Lỗi khác (4xx) raise requests.HTTPError ngay, không retry.
    - Hết lượt retry: raise lỗi cuối cùng (HTTPError hoặc lỗi kết nối).
    """
    # TODO 2
    raise NotImplementedError


def iter_orders(
    base_url: str,
    token: str,
    *,
    page_size: int = 100,
    session: requests.Session | None = None,
    max_retries: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[dict[str, Any]]:
    """Generator duyệt mọi đơn hàng qua GET {base_url}/orders?limit=..&cursor=..

    Response: {"data": [...], "next_cursor": "..." | null}. Trang đầu không gửi cursor.
    Header: Authorization: Bearer <token>.
    """
    # TODO 3
    raise NotImplementedError
