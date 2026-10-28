"""Cache-aside cho sản phẩm Olist bằng Redis."""

from __future__ import annotations

import json  # noqa: F401
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
        self.r = r  # redis.Redis(decode_responses=True) hoặc fakeredis
        self.loader = loader
        self.ttl = ttl
        self.negative_ttl = negative_ttl

    def key(self, product_id: str) -> str:
        # TODO: "product:<product_id>"
        raise NotImplementedError

    def get(self, product_id: str) -> dict | None:
        # TODO: GET; hit -> json.loads (hoặc None nếu là NONE_MARKER)
        #       miss -> loader; lưu JSON với ttl, hoặc NONE_MARKER với negative_ttl
        raise NotImplementedError

    def invalidate(self, product_id: str) -> bool:
        # TODO: DEL key, True nếu đã xoá được
        raise NotImplementedError

    def update(self, product_id: str, fields: dict, saver: Callable[[str, dict], None]) -> None:
        # TODO: saver trước, invalidate sau
        raise NotImplementedError
