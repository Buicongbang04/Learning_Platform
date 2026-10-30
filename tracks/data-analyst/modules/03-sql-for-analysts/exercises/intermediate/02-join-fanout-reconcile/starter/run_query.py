"""Chạy thử một tệp .sql của bài trên dữ liệu thật rồi in kết quả. Tệp này không được chấm.

Nạp bộ `dunnhumby-complete-journey` vào DuckDB trong bộ nhớ (bảng: transaction_data, hh_demographic, campaign_table, campaign_desc), chạy tệp .sql và in các dòng đầu:

    uv run python <thư mục bài>/starter/run_query.py fanout_audit.sql
    uv run python <thư mục bài>/starter/run_query.py fanout_audit.sql --rows 100
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

DH_TABLES = ("transaction_data", "hh_demographic", "campaign_table", "campaign_desc")


def load_dunnhumby(con: duckdb.DuckDBPyConnection, folder: Path) -> None:
    """Bốn bảng dunnhumby, tên bảng và tên cột giữ nguyên như tệp CSV."""
    for table in DH_TABLES:
        path = str(folder / f"{table}.csv").replace("'", "''")
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv('{path}', header = true)")


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
    load_dunnhumby(con, ensure("dunnhumby-complete-journey"))
    result = con.sql(path.read_text(encoding="utf-8")).df()
    print(result.head(args.rows).to_string())
    print(f"({len(result)} dòng)")


if __name__ == "__main__":
    main()
