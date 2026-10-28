"""Pipeline đơn hàng theo ngày có data contract, quarantine và backfill.

Bảng đích (DuckDB):
  fct_orders(order_id VARCHAR, customer_id VARCHAR, order_status VARCHAR, amount DOUBLE,
             purchased_at TIMESTAMP, ds DATE)
  quarantine_orders(ds DATE, row_json VARCHAR, reason VARCHAR)
"""

from __future__ import annotations

from pathlib import Path


class ContractViolation(Exception):
    """Tỉ lệ dòng vi phạm contract vượt ngưỡng: không publish partition."""


def load_contract(path: str | Path) -> dict:
    """Đọc contract YAML."""
    # TODO
    raise NotImplementedError


def validate(rows: list[dict], contract: dict) -> tuple[list[dict], list[dict]]:
    """Tách dòng đạt và dòng vi phạm.

    Dòng đạt: đã ép kiểu (amount float, order_purchase_timestamp -> datetime).
    Dòng vi phạm: dict gốc + khoá "_reason" (chuỗi mô tả vi phạm đầu tiên, có chứa tên cột).
    Với cột unique: lần xuất hiện đầu hợp lệ, các lần sau là vi phạm.
    """
    # TODO
    raise NotImplementedError


def run_partition(raw_dir: str, db_path: str, ds: str, contract_path: str, max_error_rate: float = 0.2) -> dict:
    """Xử lý file raw_dir/orders_<ds>.csv.

    - Ghi dòng vi phạm vào quarantine_orders (thay thế quarantine cũ của ds).
    - Nếu tỉ lệ vi phạm > max_error_rate: raise ContractViolation, KHÔNG đụng fct_orders của ds.
    - Ngược lại delete-insert partition ds của fct_orders.
    Trả về {"ds": ds, "loaded": n_ok, "quarantined": n_bad}.
    """
    # TODO
    raise NotImplementedError


def backfill(raw_dir: str, db_path: str, start: str, end: str, contract_path: str,
             max_error_rate: float = 0.2) -> list[dict]:
    """Chạy run_partition cho từng ngày start..end. Ngày lỗi (thiếu file, vi phạm contract) không
    làm dừng backfill: kết quả ngày đó là {"ds": ds, "error": "<mô tả>"}."""
    # TODO
    raise NotImplementedError
