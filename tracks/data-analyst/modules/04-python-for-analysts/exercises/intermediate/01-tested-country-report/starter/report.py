"""Báo cáo doanh thu theo quốc gia của Online Retail II, so hai kỳ. Dùng lại mỗi quý.

    from report import compare_periods
    table = compare_periods(tx, current=("2011-07-01", "2011-10-01"), previous=("2011-04-01", "2011-07-01"), top=5)

Định nghĩa (dùng chung cả track): dòng hợp lệ = Invoice không bắt đầu bằng "C", Quantity > 0, Price > 0;
doanh thu = Quantity * Price (GBP, doanh thu gộp). Kỳ là nửa mở [start, end).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SUMMARY_COLUMNS = ["revenue", "orders", "customers", "aov", "share"]
COMPARE_COLUMNS = ["revenue", "revenue_prev", "change", "growth", "status"]


def clean_transactions(tx: pd.DataFrame) -> pd.DataFrame:
    """Dòng hợp lệ, Invoice là str, thêm cột revenue. Không sửa tx."""
    # TODO: ép Invoice sang str trên bản sao, lọc dòng hợp lệ, thêm revenue
    raise NotImplementedError


def country_summary(tx: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Mỗi quốc gia một dòng trong kỳ [start, end): revenue, orders, customers, aov, share.

    orders = số hoá đơn khác nhau; customers = số Customer ID khác nhau (không tính dòng thiếu mã);
    aov = revenue / orders; share = revenue / tổng revenue của kỳ. Sắp revenue giảm dần.
    """
    # TODO: clean_transactions, lọc [start, end), groupby Country với agg có tên cột
    raise NotImplementedError


def compare_periods(tx: pd.DataFrame, current: tuple[str, str], previous: tuple[str, str],
                    top: int | None = None) -> pd.DataFrame:
    """So doanh thu theo quốc gia giữa hai kỳ.

    Cột: revenue (kỳ này), revenue_prev (kỳ trước), change = revenue - revenue_prev,
    growth = revenue / revenue_prev - 1 (NaN khi revenue_prev == 0),
    status = "both" | "new" (chỉ có kỳ này) | "lost" (chỉ có kỳ trước).
    Nước thiếu ở một kỳ có doanh thu 0 ở kỳ đó. Sắp revenue giảm dần, rồi revenue_prev giảm dần.
    top=N: giữ N nước đầu, gộp phần còn lại thành một dòng "Other" (status "other").
    """
    # TODO: hai country_summary, merge outer (validate, indicator), điền 0, status, top + Other, change, growth
    raise NotImplementedError
