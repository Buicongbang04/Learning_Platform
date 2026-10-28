"""Bộ check cho pipeline đơn hàng Olist (lời giải)."""

from __future__ import annotations

import sqlite3

import pandas as pd


def raw_orders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": ["o2", "o1", None, "o2", "o3"],
            "customer_id": ["c2", "c1", "c9", "c2", "c3"],
            "order_status": ["SHIPPED", " shipped ", "delivered", "Delivered", "canceled"],
            # o2 bản CŨ (08:00) đứng trước bản mới (12:00) -> bắt lỗi giữ bản gặp đầu tiên
            "updated_at": ["2018-08-01 08:00", "2018-08-01 10:00", "2018-08-01 09:00",
                           "2018-08-01 12:00", "2018-08-01 07:00"],
        }
    )


def customers() -> pd.DataFrame:
    return pd.DataFrame({"customer_id": ["c1", "c2", "c3"], "customer_state": ["SP", "RJ", "MG"]})


def payments() -> pd.DataFrame:
    return pd.DataFrame(
        {"order_id": ["o1", "o2", "o2", "o3"], "payment_value": [500.0, 100.0, 20.5, 999.0]}
    )


# ---------- Unit ----------

def check_clean_drops_null_order_id(pipeline):
    out = pipeline.clean_orders(raw_orders())
    assert out["order_id"].notna().all()
    assert "c9" not in set(out["customer_id"])


def check_clean_normalizes_status(pipeline):
    out = pipeline.clean_orders(raw_orders())
    status = dict(zip(out["order_id"], out["order_status"]))
    assert status["o1"] == "shipped"
    assert all(s == s.strip().lower() for s in out["order_status"])


def check_clean_keeps_latest_duplicate(pipeline):
    out = pipeline.clean_orders(raw_orders())
    assert list(out["order_id"]) == ["o1", "o2", "o3"]
    o2 = out[out["order_id"] == "o2"].iloc[0]
    assert o2["updated_at"] == "2018-08-01 12:00"
    assert o2["order_status"] == "delivered"


# ---------- Functional ----------

def check_revenue_excludes_canceled(pipeline):
    orders = pipeline.clean_orders(raw_orders())
    out = pipeline.revenue_by_state(orders, payments(), customers())
    revenue = dict(zip(out["customer_state"], out["revenue"]))
    assert "MG" not in revenue, "o3 bị canceled, không được tính"
    assert revenue == {"SP": 500.0, "RJ": 120.5}


def check_revenue_sorted_desc(pipeline):
    orders = pipeline.clean_orders(raw_orders())
    out = pipeline.revenue_by_state(orders, payments(), customers())
    assert list(out.columns) == ["customer_state", "revenue"]
    # SP (500) > RJ (120.5) nhưng RJ đứng trước theo alphabet -> bắt lỗi quên sort
    assert list(out["customer_state"]) == ["SP", "RJ"]


# ---------- Integration (SQLite) ----------

def check_load_is_idempotent(pipeline):
    conn = sqlite3.connect(":memory:")
    orders = pipeline.clean_orders(raw_orders())
    first = pipeline.load_orders(orders, conn)
    second = pipeline.load_orders(orders, conn)
    assert first == second == 3
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 3


def check_load_upserts_new_values(pipeline):
    conn = sqlite3.connect(":memory:")
    orders = pipeline.clean_orders(raw_orders())
    pipeline.load_orders(orders, conn)
    updated = orders.assign(order_status=["delivered", "delivered", "delivered"])
    pipeline.load_orders(updated, conn)
    status = conn.execute("SELECT order_status FROM orders WHERE order_id = 'o1'").fetchone()[0]
    assert status == "delivered"
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 3
