"""Dashboard KPI Bike Sharing bằng Streamlit + Plotly (lời giải).

    uv run streamlit run tracks/data-analyst/modules/10-bi-dashboards/exercises/basic/03-streamlit-bike-kpis/starter/app.py

Đọc `data/raw/bike-sharing-uci/day.csv` (đổi bằng biến môi trường BIKE_DAY_CSV).
Phần trên là hàm thuần (test gọi trực tiếp), phần UI nằm trong main() và chỉ chạy khi Streamlit chạy tệp này.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

# Nhãn theo Readme UCI (1 = spring) kèm khoảng ngày thật trong dữ liệu: mã 1 là 21/12-20/3, tức mùa đông.
SEASONS = {
    1: "1 · spring (21/12-20/3)",
    2: "2 · summer (21/3-20/6)",
    3: "3 · fall (21/6-22/9)",
    4: "4 · winter (23/9-20/12)",
}


def default_csv() -> Path:
    root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
    return root / "data" / "raw" / "bike-sharing-uci" / "day.csv"


def load_day(path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["dteday"])
    df["year"] = 2011 + df["yr"]
    return df


def filter_days(df: pd.DataFrame, year: int, seasons: list[int] | None = None) -> pd.DataFrame:
    mask = df["year"] == year
    if seasons:
        mask &= df["season"].isin(seasons)
    return df[mask].reset_index(drop=True)


def kpis(df: pd.DataFrame) -> dict:
    days = len(df)
    total = int(df["cnt"].sum())
    return {
        "days": days,
        "total": total,
        "per_day": total / days if days else None,
        "casual_share": df["casual"].sum() / total if total else None,
    }


def yoy(current, previous) -> float | None:
    if current is None or not previous:
        return None
    return current / previous - 1


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.assign(month=df["dteday"].dt.to_period("M").dt.to_timestamp())
        .groupby("month", as_index=False)[["casual", "registered", "cnt"]]
        .sum()
    )
    return out.sort_values("month").reset_index(drop=True)


def fmt_delta_pct(x: float | None) -> str | None:
    return None if x is None else f"{x:+.1%}"


def fmt_delta_pp(current: float | None, previous: float | None) -> str | None:
    if current is None or previous is None:
        return None
    return f"{(current - previous) * 100:+.1f} điểm %"


def main() -> None:
    import plotly.graph_objects as go
    import streamlit as st

    st.set_page_config(page_title="Bike Sharing KPI", layout="wide")

    @st.cache_data
    def cached(path: str) -> pd.DataFrame:
        return load_day(path)

    df = cached(os.environ.get("BIKE_DAY_CSV", str(default_csv())))

    st.sidebar.header("Bộ lọc")
    year = st.sidebar.selectbox("Năm", [2012, 2011])
    labels = st.sidebar.multiselect("Mùa", list(SEASONS.values()), default=list(SEASONS.values()))
    seasons = [code for code, label in SEASONS.items() if label in labels]

    current = filter_days(df, year, seasons)
    cur, prev = kpis(current), kpis(filter_days(df, year - 1, seasons))

    st.title("Lượt thuê xe đạp Capital Bikeshare")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng lượt thuê", f"{cur['total']:,}", delta=fmt_delta_pct(yoy(cur["total"], prev["total"])))
    c2.metric(
        "Lượt thuê TB/ngày",
        "n/a" if cur["per_day"] is None else f"{cur['per_day']:,.0f}",
        delta=fmt_delta_pct(yoy(cur["per_day"], prev["per_day"])),
    )
    c3.metric(
        "Tỉ trọng khách vãng lai",
        "n/a" if cur["casual_share"] is None else f"{cur['casual_share']:.1%}",
        delta=fmt_delta_pp(cur["casual_share"], prev["casual_share"]),
    )
    st.caption("Delta so với cùng các mùa của năm trước; năm đầu của dữ liệu không có delta.")

    m = monthly(current)
    fig = go.Figure()
    fig.add_bar(x=m["month"], y=m["registered"], name="registered", marker_color="#4c78a8")
    fig.add_bar(x=m["month"], y=m["casual"], name="casual", marker_color="#f58518")
    fig.update_layout(barmode="stack", title="Lượt thuê theo tháng, tách thành viên và khách vãng lai", height=380)
    st.plotly_chart(fig)

    st.subheader("5 ngày đông nhất")
    top = current.nlargest(5, "cnt")[["dteday", "cnt", "casual", "registered", "weathersit", "temp"]]
    st.dataframe(top.assign(dteday=top["dteday"].dt.date), hide_index=True)
    st.caption("Nguồn: Bike Sharing Dataset (UCI, CC BY 4.0), `day.csv`.")


if __name__ == "__main__":
    main()
