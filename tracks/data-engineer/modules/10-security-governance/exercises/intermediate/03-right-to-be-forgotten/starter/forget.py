"""Right to be forgotten: xoá dữ liệu một khách trên nhiều bảng DuckDB."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import duckdb
from cryptography.fernet import Fernet, InvalidToken

TABLES_TOUCHED = ["customers", "orders", "reviews", "user_keys"]


# ---------- Có sẵn, không cần sửa ----------

def ensure_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS user_keys (customer_unique_id VARCHAR PRIMARY KEY, dek VARCHAR)")
    con.execute("CREATE TABLE IF NOT EXISTS pii_vault (customer_unique_id VARCHAR, payload BLOB)")
    con.execute("""CREATE TABLE IF NOT EXISTS erasure_log (
        request_id VARCHAR, subject_hash VARCHAR, table_name VARCHAR,
        rows_affected INTEGER, processed_at TIMESTAMP)""")


def store_pii(con: duckdb.DuckDBPyConnection, customer_unique_id: str, payload: dict) -> None:
    """Mã hoá payload bằng DEK riêng của user (envelope rút gọn)."""
    dek = Fernet.generate_key()
    con.execute("INSERT INTO user_keys VALUES (?, ?)", [customer_unique_id, dek.decode()])
    blob = Fernet(dek).encrypt(json.dumps(payload).encode())
    con.execute("INSERT INTO pii_vault VALUES (?, ?)", [customer_unique_id, blob])


def read_vault(con: duckdb.DuckDBPyConnection, customer_unique_id: str) -> dict | None:
    row = con.execute("SELECT dek FROM user_keys WHERE customer_unique_id = ?", [customer_unique_id]).fetchone()
    blob = con.execute("SELECT payload FROM pii_vault WHERE customer_unique_id = ?", [customer_unique_id]).fetchone()
    if row is None or blob is None:
        return None
    try:
        return json.loads(Fernet(row[0].encode()).decrypt(bytes(blob[0])))
    except InvalidToken:
        return None


# ---------- Bài tập ----------

def subject_hash(customer_unique_id: str, key: bytes) -> str:
    # TODO: HMAC-SHA256 hex
    raise NotImplementedError


def find_customer_ids(con: duckdb.DuckDBPyConnection, customer_unique_id: str) -> list[str]:
    # TODO
    raise NotImplementedError


def erase_customer(con: duckdb.DuckDBPyConnection, request_id: str, customer_unique_id: str,
                   key: bytes) -> dict[str, int]:
    # TODO: idempotent theo request_id, transaction, pseudonymize orders, null review comment,
    #       crypto-shred user_keys, ghi erasure_log không có PII
    raise NotImplementedError


def verify_erased(con: duckdb.DuckDBPyConnection, customer_unique_id: str) -> list[str]:
    # TODO
    raise NotImplementedError
