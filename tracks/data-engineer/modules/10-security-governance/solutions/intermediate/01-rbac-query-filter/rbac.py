"""Lớp phân quyền trước DuckDB: RBAC + column masking + row-level security (lời giải)."""

from __future__ import annotations

import duckdb
import pandas as pd

TABLE_COLUMNS = {
    "order_items": ["order_id", "order_item_id", "product_id", "seller_id",
                    "price", "freight_value", "customer_email", "customer_cpf"],
}

POLICIES = {
    "admin": {
        "order_items": {"columns": "*", "masked": [], "row_filter": None},
    },
    "analyst": {
        "order_items": {
            "columns": ["order_id", "order_item_id", "product_id", "seller_id",
                        "price", "freight_value", "customer_email"],
            "masked": ["customer_email"],
            "row_filter": None,
        },
    },
    "seller": {
        "order_items": {
            "columns": ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"],
            "masked": [],
            "row_filter": "seller_id",  # cột phải bằng user["seller_id"]
        },
    },
}


def _policy(role: str, table: str) -> dict:
    try:
        return POLICIES[role][table]
    except KeyError:
        raise PermissionError(f"Role {role!r} không có quyền trên bảng {table!r}") from None


def _permitted(role: str, table: str) -> list[str]:
    policy = _policy(role, table)
    all_cols = TABLE_COLUMNS[table]
    if policy["columns"] == "*":
        return list(all_cols)
    return [c for c in all_cols if c in policy["columns"]]


def allowed_columns(role: str, table: str, requested: list[str]) -> list[str]:
    permitted = _permitted(role, table)
    if requested == ["*"]:
        return permitted
    denied = [c for c in requested if c not in permitted]
    if denied:
        raise PermissionError(f"Role {role!r} không được đọc cột {denied}")
    return list(requested)


def build_query(user: dict, table: str, columns: list[str], where: dict | None = None) -> tuple[str, list]:
    role = user.get("role")
    policy = _policy(role, table)
    cols = allowed_columns(role, table, columns)
    masked = set(policy["masked"])

    select = ", ".join(f'md5("{c}") AS "{c}"' if c in masked else f'"{c}"' for c in cols)
    conds: list[str] = []
    params: list = []

    if policy["row_filter"]:
        col = policy["row_filter"]
        if user.get(col) is None:
            raise PermissionError(f"User thiếu thuộc tính {col!r} cho row filter")
        conds.append(f'"{col}" = ?')
        params.append(user[col])

    for col, value in (where or {}).items():
        allowed_columns(role, table, [col])
        if col in masked:
            raise PermissionError(f"Không được lọc theo cột bị che {col!r}")
        conds.append(f'"{col}" = ?')
        params.append(value)

    sql = f'SELECT {select} FROM "{table}"'
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    return sql, params


def run_query(con: duckdb.DuckDBPyConnection, user: dict, table: str, columns: list[str],
              where: dict | None = None) -> pd.DataFrame:
    sql, params = build_query(user, table, columns, where)
    return con.execute(sql, params).df()
