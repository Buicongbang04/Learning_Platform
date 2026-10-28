"""Lời giải: logic thuần Python cho dashboard vận hành Olist."""

from __future__ import annotations

import pandas as pd


def filter_orders(df: pd.DataFrame, start, end, states=None) -> pd.DataFrame:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    mask = df["order_date"].between(start, end)  # inclusive cả hai đầu
    if states:
        mask &= df["customer_state"].isin(list(states))
    return df.loc[mask].reset_index(drop=True)


def compute_kpis(df: pd.DataFrame) -> dict:
    orders = int(df["order_id"].nunique())
    revenue = round(float(df["price"].sum()), 2)
    aov = round(revenue / orders, 2) if orders else 0.0

    # Đưa về grain đơn hàng trước khi tính tỉ lệ, tránh đơn nhiều item bị đếm nhiều lần.
    delivered = (
        df.loc[df["order_status"] == "delivered", ["order_id", "is_late"]]
        .drop_duplicates("order_id")
    )
    late_rate = round(float(delivered["is_late"].mean()), 4) if len(delivered) else None
    return {"orders": orders, "revenue": revenue, "aov": aov, "late_rate": late_rate}


def pct_change(current, previous):
    if previous is None or previous == 0 or current is None:
        return None
    return round((current - previous) / abs(previous) * 100, 1)


def daily_series(df: pd.DataFrame, start, end) -> pd.DataFrame:
    days = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D", name="order_date")
    grouped = df.groupby("order_date").agg(orders=("order_id", "nunique"), revenue=("price", "sum"))
    out = grouped.reindex(days, fill_value=0).reset_index()
    out["orders"] = out["orders"].astype(int)
    out["revenue"] = out["revenue"].astype(float)
    return out[["order_date", "orders", "revenue"]]


def format_brl(value) -> str:
    if value is None:
        return "n/a"
    sign = "-" if value < 0 else ""
    text = f"{abs(value):,.2f}"  # 1,234.50
    text = text.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{sign}R$ {text}"


def kpi_status(value, target, higher_is_better: bool = True, warn_margin: float = 0.1) -> str:
    if value is None:
        return "unknown"
    gap = (target - value) if higher_is_better else (value - target)
    if gap <= 0:
        return "ok"
    if gap <= warn_margin * abs(target):
        return "warn"
    return "bad"
