"""Các phiên bản lỗi (mutant) của pipeline. Bộ check của bạn phải bắt được từng cái.

Đừng đọc tệp này trước khi tự viết check: hãy viết check theo đặc tả trong pipeline.py.
"""

from __future__ import annotations

import pandas as pd


def clean_keeps_null_ids(orders):
    df = orders.copy()
    df["order_status"] = df["order_status"].str.strip().str.lower()
    df = df.sort_values(["order_id", "updated_at"]).drop_duplicates("order_id", keep="last")
    return df.sort_values("order_id", na_position="last").reset_index(drop=True)


def clean_status_not_normalized(orders):
    df = orders[orders["order_id"].notna()].copy()
    df = df.sort_values(["order_id", "updated_at"]).drop_duplicates("order_id", keep="last")
    return df.sort_values("order_id").reset_index(drop=True)


def clean_keeps_first_seen(orders):
    df = orders[orders["order_id"].notna()].copy()
    df["order_status"] = df["order_status"].str.strip().str.lower()
    df = df.drop_duplicates("order_id", keep="first")
    return df.sort_values("order_id").reset_index(drop=True)


def revenue_includes_canceled(orders, payments, customers):
    joined = orders.merge(payments, on="order_id").merge(customers, on="customer_id")
    out = joined.groupby("customer_state", as_index=False)["payment_value"].sum()
    out = out.rename(columns={"payment_value": "revenue"})
    out["revenue"] = out["revenue"].round(2)
    return out.sort_values("revenue", ascending=False).reset_index(drop=True)


def revenue_sorted_by_state(orders, payments, customers):
    valid = orders[orders["order_status"] != "canceled"]
    joined = valid.merge(payments, on="order_id").merge(customers, on="customer_id")
    out = joined.groupby("customer_state", as_index=False)["payment_value"].sum()
    out = out.rename(columns={"payment_value": "revenue"})
    out["revenue"] = out["revenue"].round(2)
    return out.reset_index(drop=True)


def load_appends(orders, conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS orders (order_id TEXT, customer_id TEXT, order_status TEXT, updated_at TEXT)"
    )
    rows = orders[["order_id", "customer_id", "order_status", "updated_at"]].astype(str).itertuples(index=False)
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", list(rows))
    conn.commit()
    return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]


def load_ignores_updates(orders, conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS orders ("
        "order_id TEXT PRIMARY KEY, customer_id TEXT, order_status TEXT, updated_at TEXT)"
    )
    rows = orders[["order_id", "customer_id", "order_status", "updated_at"]].astype(str).itertuples(index=False)
    conn.executemany("INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?)", list(rows))
    conn.commit()
    return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]


MUTANTS = {
    "clean_keeps_null_ids": ("clean_orders", clean_keeps_null_ids),
    "clean_status_not_normalized": ("clean_orders", clean_status_not_normalized),
    "clean_keeps_first_seen": ("clean_orders", clean_keeps_first_seen),
    "revenue_includes_canceled": ("revenue_by_state", revenue_includes_canceled),
    "revenue_sorted_by_state": ("revenue_by_state", revenue_sorted_by_state),
    "load_appends": ("load_orders", load_appends),
    "load_ignores_updates": ("load_orders", load_ignores_updates),
}

_ = pd  # pandas được dùng gián tiếp qua DataFrame truyền vào
