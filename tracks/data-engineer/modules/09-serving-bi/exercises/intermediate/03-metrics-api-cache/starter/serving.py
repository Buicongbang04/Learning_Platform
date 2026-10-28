"""Lớp serving cho API metric: validate input, query tham số hoá, phân trang, cache TTL có version.

Bảng nguồn: agg_daily_sales(order_date DATE, customer_state VARCHAR, orders BIGINT, revenue DOUBLE).
Lớp này không phụ thuộc web framework; handle_request mô phỏng một endpoint HTTP
GET /daily-sales?state=SP&start=2018-08-01&end=2018-08-31&limit=100&offset=0
"""

from __future__ import annotations

import time

import duckdb

MAX_LIMIT = 500
MAX_RANGE_DAYS = 366


class ValidationError(ValueError):
    """Tham số request không hợp lệ (map sang HTTP 400)."""


class TTLCache:
    """Cache trong bộ nhớ, mỗi key hết hạn sau `ttl` giây tính theo `clock()`.

    Thuộc tính hits, misses đếm số lần get trúng/trượt (key hết hạn tính là trượt và bị xoá).
    """

    def __init__(self, ttl: float, clock=time.monotonic):
        self.ttl = ttl
        self.clock = clock
        self.hits = 0
        self.misses = 0
        self._store: dict = {}

    def get(self, key, default=None):
        # TODO
        raise NotImplementedError

    def set(self, key, value) -> None:
        # TODO
        raise NotImplementedError


class MetricsService:
    """Phục vụ agg_daily_sales.

    data_version: hàm trả chuỗi version dữ liệu hiện tại (ví dụ thời điểm refresh cuối). Version là một
    phần của cache key, nên khi pipeline refresh bảng, request mới tự bỏ qua cache cũ.
    queries_executed: tăng 1 mỗi lần phải xuống DB (cache miss).
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, cache: TTLCache, data_version=lambda: "v1"):
        self.con = con
        self.cache = cache
        self.data_version = data_version
        self.queries_executed = 0

    def validate(self, state=None, start=None, end=None, limit=100, offset=0) -> dict:
        """Chuẩn hoá và kiểm tra tham số, raise ValidationError nếu sai:
        - state: None hoặc đúng 2 chữ cái in hoa (vd 'SP'); chữ thường được chuyển thành in hoa.
        - start, end: bắt buộc, chuỗi 'YYYY-MM-DD'; start <= end; khoảng tối đa MAX_RANGE_DAYS ngày.
        - limit: số nguyên 1..MAX_LIMIT; offset: số nguyên >= 0 (bool không được coi là số).
        Trả dict {state, start, end, limit, offset} với start/end là datetime.date.
        """
        # TODO
        raise NotImplementedError

    def get_daily_sales(self, state=None, start=None, end=None, limit=100, offset=0) -> dict:
        """Trả {"data": [...], "total": int, "limit": int, "offset": int, "data_version": str}.

        - data: các dòng {order_date: 'YYYY-MM-DD', customer_state, orders, revenue} trong khoảng ngày
          (và state nếu có), sắp theo order_date rồi customer_state, cắt theo limit/offset.
        - total: tổng số dòng khớp điều kiện (trước phân trang).
        - Dùng tham số ? cho mọi giá trị.
        - Cache theo (tham số đã chuẩn hoá, data_version).
        """
        # TODO
        raise NotImplementedError


def handle_request(service: MetricsService, query: dict[str, str]) -> tuple[int, dict]:
    """Adapter kiểu HTTP: query là dict chuỗi từ URL.

    - limit/offset là chuỗi số; không parse được thì trả 400.
    - ValidationError -> (400, {"error": <thông báo>}).
    - Thành công -> (200, body của get_daily_sales).
    """
    # TODO
    raise NotImplementedError
