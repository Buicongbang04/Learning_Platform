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
    # TODO: lưới tháng đầy đủ (pd.period_range), đếm, tỉ lệ, cờ complete
    raise NotImplementedError


def latest_complete(kpis: pd.DataFrame) -> pd.Period:
    """Tháng cuối cùng có complete == True."""
    # TODO
    raise NotImplementedError


def _count(x: float) -> str:
    # TODO: 6512 -> "6 512"
    raise NotImplementedError


def headline(name: str, previous: float, current: float, kind: str = "rate") -> str:
    """Tiêu đề kết luận cho một KPI, đúng định dạng trong README.

    kind="rate": chênh lệch tính bằng điểm phần trăm, làm tròn 1 chữ số.
    kind="count": chênh lệch tương đối, làm tròn tới phần trăm nguyên.
    kind khác → ValueError.
    """
    # TODO: đúng định dạng trong README
    raise NotImplementedError


def kpi_headline(kpis: pd.DataFrame, column: str, name: str, kind: str = "rate") -> str:
    """headline() so tháng complete mới nhất với tháng liền trước nó."""
    # TODO: dùng latest_complete và headline
    raise NotImplementedError
