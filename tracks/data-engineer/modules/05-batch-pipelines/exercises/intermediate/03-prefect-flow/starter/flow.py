"""Pipeline đơn hàng Olist viết bằng Prefect: extract (có retry) -> transform -> load (idempotent).

Chạy thử: uv run python flow.py
"""

from __future__ import annotations

import csv
from datetime import date, timedelta

import duckdb
from prefect import flow, task
from prefect.cache_policies import NO_CACHE


def fetch_rows(path: str) -> list[dict]:
    """Đọc toàn bộ CSV nguồn (đã làm sẵn). Trong thực tế đây là gọi API có thể lỗi tạm thời."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# TODO: task có retries=3, retry_delay_seconds=0, cache_policy=NO_CACHE, tên "extract"
def extract(path: str, ds: str) -> list[dict]:
    """Gọi fetch_rows(path) (qua tên hàm của module), trả về các dòng có order_purchase_timestamp thuộc ngày ds."""
    # TODO
    raise NotImplementedError


# TODO: task (cache_policy=NO_CACHE)
def transform(rows: list[dict]) -> list[tuple]:
    """Dedup theo order_id (giữ dòng sau cùng), status lower/strip, amount float.

    Trả về list tuple (order_id, order_status, amount) sắp theo order_id.
    """
    # TODO
    raise NotImplementedError


# TODO: task (cache_policy=NO_CACHE)
def load(db_path: str, rows: list[tuple], ds: str) -> int:
    """Delete-insert partition ds vào bảng daily_orders(order_id, order_status, amount, ds DATE)."""
    # TODO
    raise NotImplementedError


# TODO: flow tên "olist-daily"
def olist_daily(path: str, db_path: str, ds: str) -> dict:
    """Chạy extract -> transform -> load cho ngày ds. Trả về {"ds": ds, "rows": số dòng đã nạp}."""
    # TODO
    raise NotImplementedError


# TODO: flow tên "olist-backfill"
def backfill(path: str, db_path: str, start: str, end: str) -> list[dict]:
    """Gọi olist_daily (subflow) cho từng ngày từ start tới end (gồm cả hai đầu), tuần tự."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    import sys

    print(olist_daily(sys.argv[1], "olist.duckdb", sys.argv[2]))
