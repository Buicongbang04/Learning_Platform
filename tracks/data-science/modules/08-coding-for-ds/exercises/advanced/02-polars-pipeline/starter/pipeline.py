"""Bảng điểm seller và GMV theo tuần bằng polars lazy."""

from __future__ import annotations

import polars as pl

COLUMNS = ["seller_id", "n_orders", "revenue", "late_rate", "review_score", "bad_review_rate"]


def seller_scorecard(orders: pl.LazyFrame, items: pl.LazyFrame, reviews: pl.LazyFrame) -> pl.LazyFrame:
    """Cùng định nghĩa với slow_seller_report của bài Intermediate 03, trả LazyFrame (chưa collect).

    Cột: COLUMNS; sắp theo seller_id. Seller không có đơn nào có review: review_score và
    bad_review_rate là null.
    """
    # TODO: đơn giao xong + cờ late; review mới nhất mỗi đơn; revenue theo món; tỉ lệ theo cặp (seller, đơn)
    raise NotImplementedError


def weekly_gmv(orders: pl.LazyFrame, items: pl.LazyFrame) -> pl.LazyFrame:
    """GMV (tổng price) và số đơn của đơn giao xong theo tuần mua hàng, trả LazyFrame.

    Cột: week (Date, thứ Hai đầu tuần), gmv, orders (số đơn khác nhau), wow_growth
    (gmv / gmv tuần liền trước trong bảng - 1; null ở dòng đầu). Sắp theo week.
    """
    # TODO: dt.truncate("1w") cho ngày thứ Hai đầu tuần
    raise NotImplementedError
