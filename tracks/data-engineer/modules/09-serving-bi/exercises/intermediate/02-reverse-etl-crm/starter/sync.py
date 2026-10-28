"""Job Reverse ETL: đồng bộ hồ sơ khách hàng từ DuckDB sang CRM.

CRM là một client bất kỳ có method `upsert(batch: list[dict]) -> dict`. Nó có thể raise:
- TransientError: lỗi tạm thời (HTTP 429, 5xx, timeout) -> nên retry.
- PermanentError: lỗi vĩnh viễn (HTTP 400, dữ liệu sai, batch quá lớn) -> không retry.
"""

from __future__ import annotations

import hashlib
import json
import time

import duckdb


class TransientError(Exception):
    """Lỗi tạm thời, có thể thử lại."""


class PermanentError(Exception):
    """Lỗi vĩnh viễn, thử lại cũng vô ích."""


def build_customer_payload(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Đọc customers/orders/order_items, trả mỗi customer_unique_id một dict, sắp xếp theo external_id:

        external_id     -> customer_unique_id
        state           -> customer_state của đơn gần nhất
        total_orders    -> số đơn hợp lệ (bỏ 'canceled', 'unavailable')
        lifetime_value  -> tổng price của các đơn hợp lệ, làm tròn 2 (float)
        last_order_date -> 'YYYY-MM-DD' của đơn hợp lệ gần nhất
        segment         -> 'vip' nếu lifetime_value >= 300, 'repeat' nếu total_orders >= 2, ngược lại 'new'

    Khách không có đơn hợp lệ nào thì không xuất hiện.
    """
    # TODO: viết SQL aggregate theo customer_unique_id rồi chuyển sang list[dict]
    raise NotImplementedError


def record_hash(record: dict) -> str:
    """SHA-256 hex của record, không phụ thuộc thứ tự key."""
    # TODO
    raise NotImplementedError


def diff_records(records: list[dict], state: dict[str, str]) -> list[dict]:
    """Chỉ trả các record mới (external_id chưa có trong state) hoặc đã đổi (hash khác). Giữ thứ tự."""
    # TODO
    raise NotImplementedError


def batched(items: list, size: int) -> list[list]:
    """Chia items thành các list liên tiếp dài tối đa size. size <= 0 thì raise ValueError."""
    # TODO
    raise NotImplementedError


def send_with_retry(client, batch: list[dict], max_retries: int = 3, base_delay: float = 0.5, sleep=time.sleep):
    """Gọi client.upsert(batch). Gặp TransientError thì chờ base_delay * 2**attempt rồi thử lại
    (attempt = 0, 1, 2, …), tối đa max_retries lần thử lại. Hết lượt thì raise lỗi cuối cùng.
    PermanentError raise ngay, không retry, không sleep. Trả kết quả của client.upsert.
    """
    # TODO
    raise NotImplementedError


def run_sync(records: list[dict], client, state: dict[str, str], batch_size: int = 100,
             max_retries: int = 3, base_delay: float = 0.5, sleep=time.sleep) -> dict:
    """Đồng bộ records sang CRM, idempotent.

    - Chỉ gửi record thay đổi (diff_records), chia batch, gửi bằng send_with_retry.
    - Batch thành công: ghi hash của từng record vào state (sửa state tại chỗ).
    - Batch thất bại (PermanentError hoặc hết retry): KHÔNG ghi state, ghi nhận lỗi rồi chạy tiếp batch sau.
    - Trả dict: total (số record đầu vào), skipped (không đổi), sent (gửi thành công), failed (gửi lỗi),
      batches (số batch đã thử), failed_ids (list external_id lỗi, theo thứ tự).
    """
    # TODO
    raise NotImplementedError
