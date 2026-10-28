"""M01: nạp 9 tệp CSV Olist vào schema `raw` của PostgreSQL.

Chạy:
    docker compose -f setup/docker-compose.yml up -d postgres
    uv run python tracks/data-engineer/capstone/project/ingestion/load_postgres.py --data-dir data/raw

Yêu cầu: idempotent (chạy lại không nhân đôi), mỗi bảng nạp trong một transaction, log số dòng.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import pandas as pd

log = logging.getLogger("load_postgres")

POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "postgresql://de:de@localhost:5432/de")

# Tên tệp CSV -> tên bảng trong schema raw.
TABLES: dict[str, str] = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_name_translation",
}

# Cột ngày giờ cần ép kiểu khi đọc.
DATE_COLUMNS: dict[str, list[str]] = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
}


def read_csv(path: Path, table: str) -> pd.DataFrame:
    """Đọc một CSV, ép kiểu cột ngày. Đã xong, có thể sửa nếu muốn."""
    return pd.read_csv(path, parse_dates=DATE_COLUMNS.get(table, []))


def create_schema(conn) -> None:
    """Chạy DDL trong models/raw/00_raw_schema.sql."""
    # TODO: đọc tệp DDL và execute
    raise NotImplementedError


def load_table(conn, df: pd.DataFrame, table: str) -> int:
    """Nạp df vào raw.<table> một cách idempotent, trả về số dòng trong bảng sau khi nạp.

    Gợi ý: COPY vào bảng tạm rồi INSERT ... ON CONFLICT DO UPDATE, tất cả trong một transaction.
    """
    # TODO
    raise NotImplementedError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    import psycopg

    with psycopg.connect(POSTGRES_DSN) as conn:
        create_schema(conn)
        for filename, table in TABLES.items():
            df = read_csv(args.data_dir / filename, table)
            rows = load_table(conn, df, table)
            log.info("raw.%s: đọc %d dòng, bảng có %d dòng", table, len(df), rows)
            # TODO: thoát mã khác 0 nếu số dòng lệch


if __name__ == "__main__":
    main()
