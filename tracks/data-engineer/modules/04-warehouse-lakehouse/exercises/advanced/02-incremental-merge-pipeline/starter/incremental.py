"""Nạp tăng dần idempotent vào Delta silver, rồi tính lại gold theo ngày bị ảnh hưởng.

TODO (trả lời ngắn, thay đoạn này):
- Vì sao trả về "ngày bị ảnh hưởng" thay vì tính lại cả gold?
- Khi nào cách này cho kết quả sai, và sửa thế nào?
"""

from __future__ import annotations

import datetime as dt

import duckdb  # noqa: F401
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake  # noqa: F401


def load_increment(silver_path: str, batch: pa.Table) -> set[dt.date]:
    """Khử trùng batch, MERGE vào silver (chỉ khi mới hơn), trả order_date của các đơn thực sự thay đổi."""
    # TODO
    raise NotImplementedError


def refresh_gold(silver_path: str, gold_path: str, dates: set[dt.date]) -> int:
    """Tính lại daily_revenue chỉ cho các ngày trong `dates`."""
    # TODO
    raise NotImplementedError


def run_batch(silver_path: str, gold_path: str, batch: pa.Table) -> set[dt.date]:
    # TODO
    raise NotImplementedError
