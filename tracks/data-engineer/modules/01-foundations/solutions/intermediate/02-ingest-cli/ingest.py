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
    order_id = (row.get("order_id") or "").strip()
    customer_id = (row.get("customer_id") or "").strip()
    status = (row.get("order_status") or "").strip()
    raw_ts = (row.get("order_purchase_timestamp") or "").strip()

    if not order_id:
        raise ValueError("order_id rỗng")
    if not customer_id:
        raise ValueError("customer_id rỗng")
    if status not in VALID_STATUSES:
        raise ValueError(f"order_status không hợp lệ: {status!r}")
    try:
        ts = datetime.strptime(raw_ts, TS_FORMAT)
    except ValueError:
        raise ValueError(f"order_purchase_timestamp sai định dạng: {raw_ts!r}") from None
    return Order(order_id, customer_id, status, ts)


def ensure_schema(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                order_status TEXT NOT NULL,
                order_purchase_timestamp TEXT NOT NULL
            )
            """
        )


UPSERT_SQL = """
INSERT INTO orders (order_id, customer_id, order_status, order_purchase_timestamp)
VALUES (?, ?, ?, ?)
ON CONFLICT(order_id) DO UPDATE SET
    customer_id = excluded.customer_id,
    order_status = excluded.order_status,
    order_purchase_timestamp = excluded.order_purchase_timestamp
"""


def upsert(conn: sqlite3.Connection, orders: Iterable[Order]) -> int:
    """Ghi một lô trong một transaction, trả số dòng đã ghi."""
    params = [
        (o.order_id, o.customer_id, o.order_status, o.order_purchase_timestamp.strftime(TS_FORMAT))
        for o in orders
    ]
    with conn:  # commit khi thành công, rollback khi có exception
        conn.executemany(UPSERT_SQL, params)
    return len(params)


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

    if not args.csv_path.is_file():
        logger.error("Không thấy tệp đầu vào %s", args.csv_path)
        return 1
    rejects_path = args.rejects or args.csv_path.with_name(args.csv_path.name + ".rejects.csv")

    loaded = rejected = 0
    with open(args.csv_path, newline="", encoding="utf-8") as src:
        reader = csv.DictReader(src)
        fieldnames = reader.fieldnames or []
        missing = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
        if missing:
            logger.error("Header thiếu cột %s", ", ".join(missing))
            return 1

        conn = sqlite3.connect(args.db)
        try:
            ensure_schema(conn)
            with open(rejects_path, "w", newline="", encoding="utf-8") as rej:
                writer = csv.DictWriter(rej, fieldnames=[*fieldnames, "reason"])
                writer.writeheader()
                batch: list[Order] = []
                # line 1 là header nên dòng dữ liệu bắt đầu từ 2
                for line_no, row in enumerate(reader, start=2):
                    try:
                        batch.append(validate(row))
                    except ValueError as exc:
                        rejected += 1
                        writer.writerow({**row, "reason": str(exc)})
                        logger.warning("Dòng %d bị từ chối: %s", line_no, exc)
                        continue
                    if len(batch) >= args.batch_size:
                        loaded += upsert(conn, batch)
                        batch.clear()
                if batch:
                    loaded += upsert(conn, batch)
        finally:
            conn.close()

    logger.info("loaded=%d rejected=%d rejects_file=%s", loaded, rejected, rejects_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
