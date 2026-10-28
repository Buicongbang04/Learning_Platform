"""Pipeline đơn hàng Olist cần được kiểm thử. KHÔNG sửa tệp này.

Hành vi mong đợi (đặc tả):

- clean_orders(orders):
    * bỏ dòng có order_id rỗng (None/NaN);
    * order_status bỏ khoảng trắng hai đầu và viết thường;
    * nếu một order_id xuất hiện nhiều lần, giữ bản có updated_at MỚI NHẤT;
    * trả DataFrame sắp theo order_id, index 0..n-1, cột giữ nguyên.
- revenue_by_state(orders, payments, customers):
    * tổng payment_value theo customer_state, KHÔNG tính đơn có order_status == "canceled";
    * orders đầu vào đã được clean; kết quả có cột [customer_state, revenue],
      revenue làm tròn 2 chữ số, sắp revenue giảm dần.
- load_orders(orders, conn):
    * tạo bảng orders(order_id PRIMARY KEY, customer_id, order_status, updated_at) nếu chưa có;
    * upsert: chạy lại với cùng dữ liệu không nhân đôi dòng, dữ liệu mới ghi đè bản cũ;
    * trả về số dòng hiện có trong bảng.
"""

from __future__ import annotations

import sqlite3

import pandas as pd


def clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    df = orders[orders["order_id"].notna()].copy()
    df["order_status"] = df["order_status"].str.strip().str.lower()
    df = df.sort_values(["order_id", "updated_at"]).drop_duplicates("order_id", keep="last")
    return df.sort_values("order_id").reset_index(drop=True)


def revenue_by_state(orders: pd.DataFrame, payments: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    valid = orders[orders["order_status"] != "canceled"]
    joined = valid.merge(payments, on="order_id").merge(customers, on="customer_id")
    out = joined.groupby("customer_state", as_index=False)["payment_value"].sum()
    out = out.rename(columns={"payment_value": "revenue"})
    out["revenue"] = out["revenue"].round(2)
    return out.sort_values("revenue", ascending=False).reset_index(drop=True)


def load_orders(orders: pd.DataFrame, conn: sqlite3.Connection) -> int:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS orders ("
        "order_id TEXT PRIMARY KEY, customer_id TEXT, order_status TEXT, updated_at TEXT)"
    )
    rows = orders[["order_id", "customer_id", "order_status", "updated_at"]].astype(str).itertuples(index=False)
    conn.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?) "
        "ON CONFLICT(order_id) DO UPDATE SET customer_id=excluded.customer_id, "
        "order_status=excluded.order_status, updated_at=excluded.updated_at",
        list(rows),
    )
    conn.commit()
    return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
