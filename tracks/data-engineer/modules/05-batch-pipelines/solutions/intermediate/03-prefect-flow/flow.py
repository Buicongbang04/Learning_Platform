"""Pipeline đơn hàng Olist viết bằng Prefect: extract (có retry) -> transform -> load (idempotent).

Chạy thử: uv run python flow.py <orders.csv> 2018-01-01
"""

from __future__ import annotations

import csv
from datetime import date, timedelta

import duckdb
from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE


def fetch_rows(path: str) -> list[dict]:
    """Đọc toàn bộ CSV nguồn (đã làm sẵn). Trong thực tế đây là gọi API có thể lỗi tạm thời."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@task(name="extract", retries=3, retry_delay_seconds=0, cache_policy=NO_CACHE)
def extract(path: str, ds: str) -> list[dict]:
    """Gọi fetch_rows(path), trả về các dòng có order_purchase_timestamp thuộc ngày ds."""
    return [r for r in fetch_rows(path) if r["order_purchase_timestamp"][:10] == ds]


@task(name="transform", cache_policy=NO_CACHE)
def transform(rows: list[dict]) -> list[tuple]:
    """Dedup theo order_id (giữ dòng sau cùng), status lower/strip, amount float."""
    latest: dict[str, tuple] = {}
    for r in rows:
        if not r.get("order_id"):
            continue
        latest[r["order_id"]] = (r["order_id"], r["order_status"].strip().lower(), float(r["amount"]))
    return sorted(latest.values())


@task(name="load", cache_policy=NO_CACHE)
def load(db_path: str, rows: list[tuple], ds: str) -> int:
    """Delete-insert partition ds vào bảng daily_orders(order_id, order_status, amount, ds DATE)."""
    con = duckdb.connect(db_path)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS daily_orders (order_id VARCHAR, order_status VARCHAR, amount DOUBLE, ds DATE)"
        )
        con.execute("BEGIN")
        try:
            con.execute("DELETE FROM daily_orders WHERE ds = CAST(? AS DATE)", [ds])
            if rows:
                con.executemany(
                    "INSERT INTO daily_orders VALUES (?, ?, ?, CAST(? AS DATE))",
                    [(*r, ds) for r in rows],
                )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    finally:
        con.close()
    return len(rows)


@flow(name="olist-daily")
def olist_daily(path: str, db_path: str, ds: str) -> dict:
    """Chạy extract -> transform -> load cho ngày ds."""
    n = load(db_path, transform(extract(path, ds)), ds)
    get_run_logger().info("Nạp %s dòng cho %s", n, ds)
    return {"ds": ds, "rows": n}


@flow(name="olist-backfill")
def backfill(path: str, db_path: str, start: str, end: str) -> list[dict]:
    """Gọi olist_daily (subflow) cho từng ngày từ start tới end, tuần tự."""
    results = []
    day, last = date.fromisoformat(start), date.fromisoformat(end)
    while day <= last:
        results.append(olist_daily(path, db_path, day.isoformat()))
        day += timedelta(days=1)
    return results


if __name__ == "__main__":
    import sys

    print(olist_daily(sys.argv[1], "olist.duckdb", sys.argv[2]))
