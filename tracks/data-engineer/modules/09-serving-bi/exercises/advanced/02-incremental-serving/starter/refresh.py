"""Duy trì bảng serving agg_daily_sales theo kiểu incremental, kết quả luôn bằng full rebuild.

Hợp đồng dữ liệu nguồn (xem README):
- orders.updated_at tăng mỗi khi đơn hoặc item của đơn thay đổi.
- Đơn bị xoá cứng được ghi vào orders_deleted(order_id, order_purchase_timestamp, deleted_at).
- Chỉ tính đơn có order_status NOT IN ('canceled', 'unavailable').
"""

from __future__ import annotations

import datetime as dt

import duckdb

AGG_DDL = """
CREATE TABLE IF NOT EXISTS agg_daily_sales (
    order_date     DATE,
    customer_state VARCHAR,
    orders         BIGINT,
    revenue        DOUBLE,
    PRIMARY KEY (order_date, customer_state)
)
"""

STATE_DDL = """
CREATE TABLE IF NOT EXISTS _refresh_state (
    table_name VARCHAR PRIMARY KEY,
    watermark  TIMESTAMP
)
"""


def full_rebuild(con: duckdb.DuckDBPyConnection) -> None:
    """Tính lại toàn bộ agg_daily_sales từ nguồn và đặt watermark = thời điểm thay đổi lớn nhất đã thấy."""
    # TODO
    raise NotImplementedError


def incremental_refresh(con: duckdb.DuckDBPyConnection, lookback: dt.timedelta = dt.timedelta(0)) -> list[str]:
    """Chỉ tính lại các ngày bị ảnh hưởng bởi thay đổi kể từ watermark (trừ lookback).

    - Lần đầu (chưa có watermark) xử lý như full rebuild.
    - Ngày bị ảnh hưởng: ngày đặt của các đơn có updated_at > watermark - lookback, và của các đơn trong
      orders_deleted có deleted_at > watermark - lookback.
    - Xoá rồi tính lại đúng các ngày đó; ngày không còn đơn nào thì không còn dòng.
    - Cập nhật watermark trong cùng transaction với dữ liệu.
    - Trả danh sách ngày đã tính lại, dạng 'YYYY-MM-DD', sắp tăng dần.
    """
    # TODO
    raise NotImplementedError
