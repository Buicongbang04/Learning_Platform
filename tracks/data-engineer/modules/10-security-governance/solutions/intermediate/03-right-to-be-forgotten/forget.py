"""Right to be forgotten: xoá dữ liệu một khách trên nhiều bảng DuckDB (lời giải)."""

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
    return hmac.new(key, customer_unique_id.encode("utf-8"), hashlib.sha256).hexdigest()


def find_customer_ids(con: duckdb.DuckDBPyConnection, customer_unique_id: str) -> list[str]:
    rows = con.execute(
        "SELECT customer_id FROM customers WHERE customer_unique_id = ? ORDER BY customer_id",
        [customer_unique_id],
    ).fetchall()
    return [r[0] for r in rows]


def _count(con, sql: str, params: list) -> int:
    return con.execute(sql, params).fetchone()[0]


def erase_customer(con: duckdb.DuckDBPyConnection, request_id: str, customer_unique_id: str,
                   key: bytes) -> dict[str, int]:
    previous = con.execute(
        "SELECT table_name, rows_affected FROM erasure_log WHERE request_id = ?", [request_id]
    ).fetchall()
    if previous:
        return {table: int(n) for table, n in previous}

    result: dict[str, int] = {}
    con.begin()
    try:
        ids = find_customer_ids(con, customer_unique_id)
        placeholders = ", ".join("?" for _ in ids) or "NULL"

        # 1. reviews: bỏ free text có thể chứa PII, giữ điểm số
        result["reviews"] = _count(
            con, f"""SELECT count(*) FROM reviews WHERE order_id IN
                     (SELECT order_id FROM orders WHERE customer_id IN ({placeholders}))""", ids)
        con.execute(
            f"""UPDATE reviews SET review_comment_message = NULL WHERE order_id IN
                (SELECT order_id FROM orders WHERE customer_id IN ({placeholders}))""", ids)

        # 2. orders: giữ dòng cho aggregate, cắt liên kết bằng pseudonym ngẫu nhiên
        result["orders"] = _count(
            con, f"SELECT count(*) FROM orders WHERE customer_id IN ({placeholders})", ids)
        for old_id in ids:
            con.execute("UPDATE orders SET customer_id = ? WHERE customer_id = ?",
                        ["anon_" + uuid.uuid4().hex, old_id])

        # 3. customers: xoá PII
        result["customers"] = _count(
            con, "SELECT count(*) FROM customers WHERE customer_unique_id = ?", [customer_unique_id])
        con.execute("DELETE FROM customers WHERE customer_unique_id = ?", [customer_unique_id])

        # 4. crypto-shredding: xoá DEK, payload mã hoá trong vault/backup thành vô dụng
        result["user_keys"] = _count(
            con, "SELECT count(*) FROM user_keys WHERE customer_unique_id = ?", [customer_unique_id])
        con.execute("DELETE FROM user_keys WHERE customer_unique_id = ?", [customer_unique_id])

        h = subject_hash(customer_unique_id, key)
        for table in TABLES_TOUCHED:
            con.execute(
                "INSERT INTO erasure_log VALUES (?, ?, ?, ?, current_timestamp)",
                [request_id, h, table, result[table]],
            )
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {t: result[t] for t in TABLES_TOUCHED}


def verify_erased(con: duckdb.DuckDBPyConnection, customer_unique_id: str) -> list[str]:
    problems = []
    if find_customer_ids(con, customer_unique_id):
        problems.append("customers vẫn còn dòng")
    if _count(con, "SELECT count(*) FROM user_keys WHERE customer_unique_id = ?", [customer_unique_id]):
        problems.append("user_keys vẫn còn DEK")
    if read_vault(con, customer_unique_id) is not None:
        problems.append("pii_vault vẫn giải mã được")
    return problems
