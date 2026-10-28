"""Nạp CSV orders vào SQLite: validate, reject, upsert theo lô, logging, exit code.

Chạy: uv run python ingest.py data/orders.csv --db olist.db
"""

from __future__ import annotations

import argparse
import csv
import logging
import sqlite3
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("ingest")

VALID_STATUSES = {
    "created",
    "approved",
    "invoiced",
    "processing",
    "shipped",
    "delivered",
    "unavailable",
    "canceled",
}
REQUIRED_COLUMNS = ["order_id", "customer_id", "order_status", "order_purchase_timestamp"]
TS_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_id: str
    order_status: str
    order_purchase_timestamp: datetime


def validate(row: dict[str, str]) -> Order:
    """Trả Order hợp lệ hoặc raise ValueError nêu lý do."""
    # TODO 1: kiểm tra id không rỗng, status hợp lệ, timestamp đúng TS_FORMAT
    raise NotImplementedError


def ensure_schema(conn: sqlite3.Connection) -> None:
    # TODO 2: CREATE TABLE IF NOT EXISTS orders (...) với order_id là PRIMARY KEY
    raise NotImplementedError


def upsert(conn: sqlite3.Connection, orders: Iterable[Order]) -> int:
    """Ghi một lô trong một transaction, trả số dòng đã ghi."""
    # TODO 3: INSERT ... ON CONFLICT(order_id) DO UPDATE, trong `with conn:`
    raise NotImplementedError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Nạp orders CSV vào SQLite")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--rejects", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # TODO 4:
    #   - csv_path không tồn tại hoặc thiếu cột bắt buộc => logger.error(...), return 1
    #   - đọc từng dòng, validate; lỗi => ghi file reject (cột gốc + reason) + logger.warning
    #   - dòng hợp lệ gom lô args.batch_size => upsert; nhớ lô cuối
    #   - logger.info("loaded=%d rejected=%d", ...), return 0
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
