"""Chạy thử một tệp .sql của bài trên dữ liệu thật rồi in kết quả. Tệp này không được chấm.

Nạp bộ `ecommerce-events` vào DuckDB trong bộ nhớ (bảng: events), chạy tệp .sql và in các dòng đầu:

    uv run python <thư mục bài>/starter/run_query.py visitor_funnel.sql
    uv run python <thư mục bài>/starter/run_query.py visitor_funnel.sql --rows 100
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT))
from data.download_dataset import ensure  # noqa: E402

def load_events(con: duckdb.DuckDBPyConnection, folder: Path) -> None:
    """Bảng `events`: mỗi dòng một sự kiện view / addtocart / transaction của một visitor."""
    path = str(folder / "clean_events.csv").replace("'", "''")
    con.execute(f"""
        CREATE TABLE events AS
        SELECT visitorid AS visitor_id, event, itemid AS item_id,
               make_timestamp("timestamp" * 1000) AS event_time,  -- epoch mili giây -> TIMESTAMP (UTC)
               nullif(transactionid, 'NA') AS transaction_id
        FROM read_csv('{path}', header = true, types = {{'transactionid': 'VARCHAR'}})""")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sql", help="tệp .sql (tên tệp trong starter/ hoặc đường dẫn)")
    parser.add_argument("--rows", type=int, default=40, help="số dòng in ra")
    args = parser.parse_args()
    path = Path(args.sql)
    if not path.exists():
        path = HERE / args.sql
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    load_events(con, ensure("ecommerce-events"))
    result = con.sql(path.read_text(encoding="utf-8")).df()
    print(result.head(args.rows).to_string())
    print(f"({len(result)} dòng)")


if __name__ == "__main__":
    main()
