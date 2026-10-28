"""Lời giải: cache-aside cho sản phẩm Olist bằng Redis."""

from __future__ import annotations

import json
from typing import Callable

NONE_MARKER = "__none__"


class ProductCache:
    def __init__(
        self,
        r,
        loader: Callable[[str], dict | None],
        ttl: int = 300,
        negative_ttl: int = 30,
    ):
        self.r = r
        self.loader = loader
        self.ttl = ttl
        self.negative_ttl = negative_ttl

    def key(self, product_id: str) -> str:
        return f"product:{product_id}"

    def get(self, product_id: str) -> dict | None:
        key = self.key(product_id)
        cached = self.r.get(key)
        if cached is not None:
            return None if cached == NONE_MARKER else json.loads(cached)

        doc = self.loader(product_id)
        if doc is None:
            self.r.set(key, NONE_MARKER, ex=self.negative_ttl)
        else:
            self.r.set(key, json.dumps(doc, default=str), ex=self.ttl)
        return doc

    def invalidate(self, product_id: str) -> bool:
        return self.r.delete(self.key(product_id)) > 0

    def update(self, product_id: str, fields: dict, saver: Callable[[str, dict], None]) -> None:
        saver(product_id, fields)  # ném lỗi thì dừng ở đây, cache cũ vẫn khớp DB cũ
        self.invalidate(product_id)
