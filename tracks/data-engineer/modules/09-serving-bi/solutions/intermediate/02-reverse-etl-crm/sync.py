"""Lời giải: job Reverse ETL đồng bộ hồ sơ khách hàng từ DuckDB sang CRM."""

from __future__ import annotations

import hashlib
import json
import time

import duckdb


class TransientError(Exception):
    """Lỗi tạm thời, có thể thử lại."""


class PermanentError(Exception):
    """Lỗi vĩnh viễn, thử lại cũng vô ích."""


PAYLOAD_SQL = """
WITH valid_orders AS (
    SELECT c.customer_unique_id, c.customer_state, o.order_id, o.order_purchase_timestamp
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
),
order_value AS (
    SELECT order_id, SUM(price) AS value FROM order_items GROUP BY order_id
)
SELECT
    v.customer_unique_id                                      AS external_id,
    arg_max(v.customer_state, v.order_purchase_timestamp)     AS state,
    COUNT(DISTINCT v.order_id)                                AS total_orders,
    ROUND(COALESCE(SUM(ov.value), 0), 2)                      AS lifetime_value,
    strftime(MAX(v.order_purchase_timestamp), '%Y-%m-%d')     AS last_order_date
FROM valid_orders v
LEFT JOIN order_value ov ON ov.order_id = v.order_id
GROUP BY v.customer_unique_id
ORDER BY external_id
"""


def _segment(total_orders: int, lifetime_value: float) -> str:
    if lifetime_value >= 300:
        return "vip"
    if total_orders >= 2:
        return "repeat"
    return "new"


def build_customer_payload(con: duckdb.DuckDBPyConnection) -> list[dict]:
    cur = con.execute(PAYLOAD_SQL)
    cols = [d[0] for d in cur.description]
    records = []
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        r["total_orders"] = int(r["total_orders"])
        r["lifetime_value"] = float(r["lifetime_value"])
        r["segment"] = _segment(r["total_orders"], r["lifetime_value"])
        records.append(r)
    return records


def record_hash(record: dict) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def diff_records(records: list[dict], state: dict[str, str]) -> list[dict]:
    return [r for r in records if state.get(r["external_id"]) != record_hash(r)]


def batched(items: list, size: int) -> list[list]:
    if size <= 0:
        raise ValueError("size phải > 0")
    return [items[i:i + size] for i in range(0, len(items), size)]


def send_with_retry(client, batch: list[dict], max_retries: int = 3, base_delay: float = 0.5, sleep=time.sleep):
    attempt = 0
    while True:
        try:
            return client.upsert(batch)
        except TransientError:
            if attempt >= max_retries:
                raise
            sleep(base_delay * 2 ** attempt)
            attempt += 1


def run_sync(records: list[dict], client, state: dict[str, str], batch_size: int = 100,
             max_retries: int = 3, base_delay: float = 0.5, sleep=time.sleep) -> dict:
    changed = diff_records(records, state)
    summary = {"total": len(records), "skipped": len(records) - len(changed),
               "sent": 0, "failed": 0, "batches": 0, "failed_ids": []}
    for batch in batched(changed, batch_size):
        summary["batches"] += 1
        try:
            send_with_retry(client, batch, max_retries=max_retries, base_delay=base_delay, sleep=sleep)
        except (TransientError, PermanentError):
            summary["failed"] += len(batch)
            summary["failed_ids"].extend(r["external_id"] for r in batch)
            continue
        # Chỉ ghi state sau khi CRM xác nhận: job chết giữa chừng thì lần sau gửi lại phần thiếu.
        for r in batch:
            state[r["external_id"]] = record_hash(r)
        summary["sent"] += len(batch)
    return summary
