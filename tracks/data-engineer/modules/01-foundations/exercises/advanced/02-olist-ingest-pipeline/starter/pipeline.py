"""Pipeline nạp ba bảng Olist (customers, orders, order_items) vào SQLite.

Chạy:
    uv run python pipeline.py <thư mục CSV> --db olist.db

Bạn tự thiết kế cấu trúc code. Yêu cầu đầy đủ ở README.md của bài. Gợi ý cách chia:

    extract    đọc CSV theo lô (generator)
    validate   kiểm tra từng dòng theo kiểu dữ liệu và tập giá trị hợp lệ
    load       upsert vào bảng đích, kiểm tra khoá ngoại, ghi rejects
    audit      ghi load_runs (run_id, started_at, finished_at, status, rows_loaded, rows_rejected)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger("pipeline")

FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
}

# TODO: DDL cho customers, orders, order_items (PK, FK), rejects, load_runs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Nạp Olist CSV vào SQLite")
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # TODO: kiểm tra đầu vào, mở run trong load_runs, nạp theo thứ tự khoá ngoại,
    #       all-or-nothing cho cả lần chạy, cập nhật load_runs, trả exit code
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
