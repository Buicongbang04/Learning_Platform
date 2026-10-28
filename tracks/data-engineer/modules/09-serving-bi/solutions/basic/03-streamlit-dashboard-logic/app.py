"""Dashboard vận hành Olist bằng Streamlit. Tệp này chỉ lo UI, mọi tính toán nằm ở dashboard_logic.py.

Chạy: uv run streamlit run tracks/data-engineer/modules/09-serving-bi/exercises/basic/03-streamlit-dashboard-logic/starter/app.py
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st

import dashboard_logic as logic


@st.cache_data(ttl=600)
def load_data() -> pd.DataFrame:
    """Dữ liệu demo. Thực tế: query bảng serving (DuckDB/Postgres) với tham số, không ghép chuỗi."""
    rng = np.random.default_rng(42)
    n = 3000
    order_ids = [f"o{i // 2}" for i in range(n)]  # mỗi đơn 2 item
    days = pd.to_datetime("2018-07-01") + pd.to_timedelta(rng.integers(0, 62, n // 2).repeat(2), unit="D")
    states = rng.choice(["SP", "RJ", "MG", "RS", "PR"], n // 2, p=[0.4, 0.2, 0.2, 0.1, 0.1]).repeat(2)
    status = rng.choice(["delivered", "shipped", "canceled"], n // 2, p=[0.85, 0.1, 0.05]).repeat(2)
    late = (rng.random(n // 2) < 0.08).repeat(2)
    return pd.DataFrame({
        "order_id": order_ids,
        "order_date": days,
        "customer_state": states,
        "order_status": status,
        "price": rng.gamma(2.0, 60.0, n).round(2),
        "is_late": late,
    })


COLORS = {"ok": "normal", "warn": "off", "bad": "inverse", "unknown": "off"}

st.set_page_config(page_title="Olist Ops", layout="wide")
st.title("Vận hành đơn hàng Olist")

data = load_data()
with st.sidebar:
    start, end = st.date_input("Khoảng ngày", value=(dt.date(2018, 8, 1), dt.date(2018, 8, 31)))
    states = st.multiselect("State", sorted(data["customer_state"].unique()))
    late_target = st.number_input("Target late rate", value=0.05, step=0.01)

current = logic.filter_orders(data, start, end, states)
span = (pd.Timestamp(end) - pd.Timestamp(start)).days + 1
prev_end = pd.Timestamp(start) - pd.Timedelta(days=1)
previous = logic.filter_orders(data, prev_end - pd.Timedelta(days=span - 1), prev_end, states)

k, kp = logic.compute_kpis(current), logic.compute_kpis(previous)
c1, c2, c3, c4 = st.columns(4)
for col, label, key, fmt in [
    (c1, "Đơn", "orders", str),
    (c2, "Doanh thu", "revenue", logic.format_brl),
    (c3, "AOV", "aov", logic.format_brl),
]:
    delta = logic.pct_change(k[key], kp[key])
    col.metric(label, fmt(k[key]), None if delta is None else f"{delta}%")

status = logic.kpi_status(k["late_rate"], late_target, higher_is_better=False)
late_text = "n/a" if k["late_rate"] is None else f"{k['late_rate']:.1%}"
c4.metric(f"Late rate (target {late_target:.0%})", late_text, status, delta_color=COLORS[status])

st.subheader("Xu hướng theo ngày")
st.line_chart(logic.daily_series(current, start, end), x="order_date", y=["orders", "revenue"])
st.caption(f"Dữ liệu cập nhật lúc {dt.datetime.now():%H:%M}")
