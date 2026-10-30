"""Dashboard KPI Bike Sharing bằng Streamlit + Plotly.

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
    """Đọc day.csv, `dteday` kiểu ngày, thêm cột `year` = 2011 + yr."""
    # TODO
    raise NotImplementedError


def filter_days(df: pd.DataFrame, year: int, seasons: list[int] | None = None) -> pd.DataFrame:
    """Lọc theo năm và danh sách mã mùa. `seasons` rỗng hoặc None: không lọc mùa. Index đánh lại từ 0."""
    # TODO
    raise NotImplementedError


def kpis(df: pd.DataFrame) -> dict:
    """{"days", "total", "per_day", "casual_share"}. Không có ngày nào: per_day và casual_share là None.

    casual_share = tổng casual / tổng cnt.
    """
    # TODO
    raise NotImplementedError


def yoy(current, previous) -> float | None:
    """current / previous - 1; None khi một trong hai là None hoặc previous = 0."""
    # TODO
    raise NotImplementedError


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Cột month (Timestamp ngày đầu tháng), casual, registered, cnt (tổng theo tháng), sắp theo month."""
    # TODO
    raise NotImplementedError


def fmt_delta_pct(x: float | None) -> str | None:
    return None if x is None else f"{x:+.1%}"


def fmt_delta_pp(current: float | None, previous: float | None) -> str | None:
    if current is None or previous is None:
        return None
    return f"{(current - previous) * 100:+.1f} điểm %"


def main() -> None:
    import plotly.graph_objects as go  # noqa: F401  (dùng cho biểu đồ theo tháng)
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
    # TODO 1: ba st.metric trên một hàng (st.columns(3)), nhãn và định dạng đúng như đề bài:
    #   "Tổng lượt thuê" f"{total:,}", "Lượt thuê TB/ngày" f"{per_day:,.0f}", "Tỉ trọng khách vãng lai" f"{share:.1%}";
    #   delta so với cùng các mùa năm trước: fmt_delta_pct(yoy(...)) cho hai metric đầu, fmt_delta_pp(...) cho tỉ trọng.
    # TODO 2: stacked bar theo tháng (registered + casual) bằng plotly, hiện bằng st.plotly_chart.
    # TODO 3: drill-down: st.subheader("5 ngày đông nhất") + st.dataframe 5 ngày cnt cao nhất, sắp giảm dần
    #   (cột dteday, cnt, casual, registered, weathersit, temp), rồi st.caption ghi nguồn dữ liệu.
    raise NotImplementedError


if __name__ == "__main__":
    main()
