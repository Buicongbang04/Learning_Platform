"""Bảng aggregate agg_daily_sales và kiểm tra reconcile với bảng nguồn.

Bảng nguồn: customers, orders, order_items (xem tests/fixtures/olist_small.sql).
"""

from __future__ import annotations

import duckdb

VALID_STATUS_FILTER = "o.order_status NOT IN ('canceled', 'unavailable')"

DDL = """
CREATE TABLE IF NOT EXISTS agg_daily_sales (
    order_date     DATE,
    customer_state VARCHAR,
    orders         BIGINT,
    items          BIGINT,
    revenue        DOUBLE,
    freight        DOUBLE,
    PRIMARY KEY (order_date, customer_state)
)
"""


def build_agg_daily_sales(con: duckdb.DuckDBPyConnection, start: str, end: str) -> int:
    """Tính lại agg_daily_sales cho các ngày trong [start, end] (chuỗi 'YYYY-MM-DD', tính cả hai đầu).

    - Tạo bảng nếu chưa có (dùng DDL).
    - Idempotent: chạy lại cùng khoảng ngày không nhân đôi dữ liệu; ngày ngoài khoảng không bị đụng tới.
    - Grain (order_date, customer_state); chỉ tính đơn hợp lệ (VALID_STATUS_FILTER).
    - orders = số đơn khác nhau, items = số dòng order_items, revenue = SUM(price), freight = SUM(freight_value).
    - Dùng tham số (?) cho start/end, không ghép chuỗi.
    - Trả số dòng của bảng trong khoảng [start, end] sau khi build.
    """
    # TODO: tạo bảng, xoá các ngày trong khoảng, insert lại kết quả aggregate (trong một transaction)
    raise NotImplementedError


def reconcile(con: duckdb.DuckDBPyConnection, start: str, end: str, tolerance: float = 0.01) -> dict:
    """So khớp agg_daily_sales với bảng nguồn trong khoảng [start, end].

    Trả dict:
        ok               -> bool, True nếu không có ngày nào lệch
        agg_revenue      -> float, tổng revenue trong aggregate
        src_revenue      -> float, tổng price từ nguồn (cùng bộ lọc trạng thái)
        agg_orders       -> int
        src_orders       -> int
        mismatched_dates -> list[str] 'YYYY-MM-DD' đã sắp xếp: ngày có revenue lệch quá tolerance
                            hoặc số đơn khác nhau, kể cả ngày chỉ có ở một phía.
    """
    # TODO: tính tổng hai phía và so theo từng ngày
    raise NotImplementedError
