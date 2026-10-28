"""Lớp phân quyền trước DuckDB: RBAC + column masking + row-level security."""

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


def allowed_columns(role: str, table: str, requested: list[str]) -> list[str]:
    # TODO: deny by default; mở rộng "*"; PermissionError nếu có cột không được phép
    raise NotImplementedError


def build_query(user: dict, table: str, columns: list[str], where: dict | None = None) -> tuple[str, list]:
    # TODO: SELECT các cột (md5 cho cột bị che), row filter, where có tham số
    raise NotImplementedError


def run_query(con: duckdb.DuckDBPyConnection, user: dict, table: str, columns: list[str],
              where: dict | None = None) -> pd.DataFrame:
    # TODO
    raise NotImplementedError
