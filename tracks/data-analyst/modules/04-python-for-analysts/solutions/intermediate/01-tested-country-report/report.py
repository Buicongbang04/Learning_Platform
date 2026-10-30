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
    sales = tx.assign(Invoice=tx["Invoice"].astype(str))
    valid = ~sales["Invoice"].str.startswith("C") & (sales["Quantity"] > 0) & (sales["Price"] > 0)
    sales = sales[valid].copy()
    sales["revenue"] = sales["Quantity"] * sales["Price"]
    return sales


def country_summary(tx: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Mỗi quốc gia một dòng trong kỳ [start, end): revenue, orders, customers, aov, share.

    orders = số hoá đơn khác nhau; customers = số Customer ID khác nhau (không tính dòng thiếu mã);
    aov = revenue / orders; share = revenue / tổng revenue của kỳ. Sắp revenue giảm dần.
    """
    sales = clean_transactions(tx)
    sales = sales[(sales["InvoiceDate"] >= pd.Timestamp(start)) & (sales["InvoiceDate"] < pd.Timestamp(end))]
    out = sales.groupby("Country").agg(
        revenue=("revenue", "sum"),
        orders=("Invoice", "nunique"),
        customers=("Customer ID", "nunique"),
    )
    out["aov"] = out["revenue"] / out["orders"]
    out["share"] = out["revenue"] / out["revenue"].sum()
    out.index.name = "Country"
    return out[SUMMARY_COLUMNS].sort_values("revenue", ascending=False)


def compare_periods(tx: pd.DataFrame, current: tuple[str, str], previous: tuple[str, str],
                    top: int | None = None) -> pd.DataFrame:
    """So doanh thu theo quốc gia giữa hai kỳ.

    Cột: revenue (kỳ này), revenue_prev (kỳ trước), change = revenue - revenue_prev,
    growth = revenue / revenue_prev - 1 (NaN khi revenue_prev == 0),
    status = "both" | "new" (chỉ có kỳ này) | "lost" (chỉ có kỳ trước).
    Nước thiếu ở một kỳ có doanh thu 0 ở kỳ đó. Sắp revenue giảm dần, rồi revenue_prev giảm dần.
    top=N: giữ N nước đầu, gộp phần còn lại thành một dòng "Other" (status "other").
    """
    cur = country_summary(tx, *current)[["revenue"]]
    prev = country_summary(tx, *previous)[["revenue"]].rename(columns={"revenue": "revenue_prev"})
    merged = cur.merge(prev, left_index=True, right_index=True, how="outer",
                       validate="one_to_one", indicator=True)
    merged[["revenue", "revenue_prev"]] = merged[["revenue", "revenue_prev"]].fillna(0.0)
    merged["status"] = merged["_merge"].map({"both": "both", "left_only": "new", "right_only": "lost"}).astype(str)
    merged = merged.sort_values(["revenue", "revenue_prev"], ascending=False)
    if top is not None and len(merged) > top:
        rest = merged.iloc[top:]
        other = pd.DataFrame({"revenue": [rest["revenue"].sum()], "revenue_prev": [rest["revenue_prev"].sum()],
                              "status": ["other"]}, index=pd.Index(["Other"]))
        merged = pd.concat([merged.iloc[:top], other])
    merged["change"] = merged["revenue"] - merged["revenue_prev"]
    merged["growth"] = np.where(merged["revenue_prev"] > 0,
                                merged["revenue"] / merged["revenue_prev"].where(merged["revenue_prev"] > 0) - 1,
                                np.nan)
    merged.index.name = "Country"
    return merged[COMPARE_COLUMNS]
