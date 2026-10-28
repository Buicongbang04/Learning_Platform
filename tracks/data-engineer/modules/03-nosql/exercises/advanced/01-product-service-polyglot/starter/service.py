"""Dịch vụ sản phẩm polyglot: MongoDB (nguồn sự thật) + Redis (cache, leaderboard, rate limit).

TODO: viết vài đoạn giải thích thiết kế:
- Thứ tự ghi MongoDB và Redis, vì sao.
- Redis chết hoặc mất dữ liệu thì chuyện gì xảy ra, dựng lại thế nào.
- Giới hạn còn lại (race condition, độ trễ nhất quán...).
"""

from __future__ import annotations

import json  # noqa: F401
import random  # noqa: F401
import time
from uuid import uuid4  # noqa: F401

from pymongo import ReturnDocument  # noqa: F401
from pymongo.errors import DuplicateKeyError  # noqa: F401

CACHE_TTL = 300
TOP_KEY = "top_rated"


class ProductService:
    def __init__(self, db, r, clock=time.time, min_reviews: int = 3, rate_limit: int = 5, rate_window: int = 60):
        self.db = db
        self.r = r
        self.clock = clock
        self.min_reviews = min_reviews
        self.rate_limit = rate_limit
        self.rate_window = rate_window

    def get_product(self, product_id: str) -> dict | None:
        # TODO: cache-aside + lock chống stampede + TTL có jitter
        raise NotImplementedError

    def add_review(self, review: dict) -> bool:
        # TODO: insert idempotent, $inc bộ đếm, cập nhật avg_score, xoá cache, cập nhật top_rated
        raise NotImplementedError

    def top_rated(self, k: int = 10) -> list[tuple[str, float]]:
        # TODO: đọc sorted set; key không tồn tại thì dựng lại từ MongoDB
        raise NotImplementedError

    def record_view(self, user_id: str, product_id: str) -> None:
        # TODO: list 10 phần tử, mới nhất trước, không trùng
        raise NotImplementedError

    def recently_viewed(self, user_id: str) -> list[str]:
        # TODO
        raise NotImplementedError

    def allow_request(self, client_id: str) -> bool:
        # TODO: sliding window dùng self.clock()
        raise NotImplementedError
