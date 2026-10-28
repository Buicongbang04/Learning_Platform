"""Embedding đơn hàng Olist và aggregation pipeline MongoDB."""

from __future__ import annotations

from collections import defaultdict  # noqa: F401


def build_order_documents(
    orders: list[dict], items: list[dict], products: list[dict]
) -> list[dict]:
    """Bảng quan hệ -> document đơn hàng có items nhúng."""
    # TODO: map product_id -> category, gom items theo order_id, sắp theo order_item_id,
    #       dựng document theo README, total = round(sum(price + freight), 2)
    raise NotImplementedError


def revenue_by_category_pipeline(status: str = "delivered") -> list[dict]:
    """[{category, revenue, items}] sắp revenue giảm dần."""
    # TODO: $match (đầu tiên) -> $unwind -> $group -> $project -> $sort
    raise NotImplementedError


def monthly_orders_pipeline() -> list[dict]:
    """[{month: 'YYYY-MM', orders, gmv}] sắp month tăng dần."""
    # TODO: $group theo $dateToString
    raise NotImplementedError


def product_rating_pipeline(min_reviews: int = 2) -> list[dict]:
    """[{product_id, category, avg_score, n_reviews}] trên collection reviews, $lookup products."""
    # TODO: $group -> $match -> $lookup -> $unwind -> $project -> $sort
    raise NotImplementedError
