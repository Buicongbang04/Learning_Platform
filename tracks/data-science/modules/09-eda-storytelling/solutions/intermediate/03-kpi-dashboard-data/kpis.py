"""Dữ liệu cho dashboard KPI theo tháng: lưới thời gian đầy đủ, kỳ chưa chín, tiêu đề kết luận."""

from __future__ import annotations

import pandas as pd

KPI_COLUMNS = ["orders", "delivered", "late_rate", "bad_review_rate", "complete"]


def monthly_kpis(orders: pd.DataFrame, reviews: pd.DataFrame, snapshot: pd.Timestamp | None = None,
                 maturity_days: int = 30) -> pd.DataFrame:
    """KPI theo tháng mua hàng (order_purchase_timestamp).

    Index: PeriodIndex tần suất tháng, tên "month", ĐỦ mọi tháng từ tháng đầu tới tháng cuối có đơn
    (tháng không có đơn vẫn có dòng). Cột theo KPI_COLUMNS:
      orders           số đơn (mọi trạng thái); 0 nếu tháng trống
      delivered        số đơn giao xong (order_status == "delivered" và có order_delivered_customer_date)
      late_rate        tỉ lệ đơn giao xong bị trễ (so nguyên timestamp với ngày hẹn); NaN nếu không có
      bad_review_rate  tỉ lệ review_score <= 2 trên đơn giao xong có review (review mới nhất theo
                       review_answer_timestamp); NaN nếu không có
      complete         True nếu thời điểm cuối tháng + maturity_days ngày <= snapshot
    snapshot mặc định là order_purchase_timestamp lớn nhất (lúc dữ liệu được cắt).
    """
    if snapshot is None:
        snapshot = orders.order_purchase_timestamp.max()
    month = orders.order_purchase_timestamp.dt.to_period("M")
    grid = pd.period_range(month.min(), month.max(), freq="M", name="month")

    delivered_mask = (orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()
    d = orders[delivered_mask].assign(month=month[delivered_mask])
    d["late"] = d.order_delivered_customer_date > d.order_estimated_delivery_date
    latest = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
    r = d.merge(latest[["order_id", "review_score"]], on="order_id")

    out = pd.DataFrame(index=grid)
    out["orders"] = month.value_counts().reindex(grid, fill_value=0).astype(int)
    out["delivered"] = d.groupby("month").size().reindex(grid, fill_value=0).astype(int)
    out["late_rate"] = d.groupby("month").late.mean().astype(float).reindex(grid)
    out["bad_review_rate"] = (r.review_score <= 2).groupby(r.month).mean().astype(float).reindex(grid)
    month_end = grid.to_timestamp(how="end")
    out["complete"] = (month_end + pd.Timedelta(days=maturity_days)) <= snapshot
    return out[KPI_COLUMNS]


def latest_complete(kpis: pd.DataFrame) -> pd.Period:
    """Tháng cuối cùng có complete == True."""
    return kpis.index[kpis.complete.to_numpy()][-1]


def _count(x: float) -> str:
    return f"{int(round(x)):,}".replace(",", " ")


def headline(name: str, previous: float, current: float, kind: str = "rate") -> str:
    """Tiêu đề kết luận cho một KPI, đúng định dạng trong README.

    kind="rate": chênh lệch tính bằng điểm phần trăm, làm tròn 1 chữ số.
    kind="count": chênh lệch tương đối, làm tròn tới phần trăm nguyên.
    kind khác → ValueError.
    """
    if kind == "rate":
        points = round((current - previous) * 100, 1)
        if points == 0:
            return f"{name} không đổi ở {current:.1%}"
        if points > 0:
            return f"{name} tăng từ {previous:.1%} lên {current:.1%} (+{points:.1f} điểm %)"
        return f"{name} giảm từ {previous:.1%} xuống {current:.1%} (-{abs(points):.1f} điểm %)"
    if kind == "count":
        change = round((current / previous - 1) * 100)
        if change == 0:
            return f"{name} không đổi ở {_count(current)}"
        if change > 0:
            return f"{name} tăng {change}% (từ {_count(previous)} lên {_count(current)})"
        return f"{name} giảm {abs(change)}% (từ {_count(previous)} xuống {_count(current)})"
    raise ValueError(f"kind phải là 'rate' hoặc 'count', nhận {kind!r}")


def kpi_headline(kpis: pd.DataFrame, column: str, name: str, kind: str = "rate") -> str:
    """headline() so tháng complete mới nhất với tháng liền trước nó."""
    month = latest_complete(kpis)
    return headline(name, kpis.loc[month - 1, column], kpis.loc[month, column], kind)
