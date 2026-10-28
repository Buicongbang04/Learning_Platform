"""Lời giải: embedding đơn hàng Olist và aggregation pipeline MongoDB."""

from __future__ import annotations

from collections import defaultdict


def build_order_documents(
    orders: list[dict], items: list[dict], products: list[dict]
) -> list[dict]:
    category_of = {p["product_id"]: p["category"] for p in products}
    items_of: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        items_of[item["order_id"]].append(item)

    docs = []
    for order in orders:
        rows = sorted(items_of.get(order["order_id"], []), key=lambda i: i["order_item_id"])
        embedded = [
            {
                "product_id": i["product_id"],
                "seller_id": i["seller_id"],
                "category": category_of.get(i["product_id"]),
                "price": i["price"],
                "freight": i["freight_value"],
            }
            for i in rows
        ]
        docs.append(
            {
                "_id": order["order_id"],
                "customer": {"id": order["customer_id"], "state": order["customer_state"]},
                "status": order["order_status"],
                "purchased_at": order["purchased_at"],
                "items": embedded,
                "total": round(sum(i["price"] + i["freight"] for i in embedded), 2),
            }
        )
    return docs


def revenue_by_category_pipeline(status: str = "delivered") -> list[dict]:
    return [
        {"$match": {"status": status}},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.category", "revenue": {"$sum": "$items.price"}, "items": {"$sum": 1}}},
        {"$project": {"_id": 0, "category": "$_id", "revenue": 1, "items": 1}},
        {"$sort": {"revenue": -1}},
    ]


def monthly_orders_pipeline() -> list[dict]:
    return [
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m", "date": "$purchased_at"}},
                "orders": {"$sum": 1},
                "gmv": {"$sum": "$total"},
            }
        },
        {"$project": {"_id": 0, "month": "$_id", "orders": 1, "gmv": 1}},
        {"$sort": {"month": 1}},
    ]


def product_rating_pipeline(min_reviews: int = 2) -> list[dict]:
    return [
        {"$group": {"_id": "$product_id", "avg_score": {"$avg": "$score"}, "n_reviews": {"$sum": 1}}},
        {"$match": {"n_reviews": {"$gte": min_reviews}}},
        {"$lookup": {"from": "products", "localField": "_id", "foreignField": "_id", "as": "product"}},
        {"$unwind": "$product"},
        {
            "$project": {
                "_id": 0,
                "product_id": "$_id",
                "category": "$product.category",
                "avg_score": 1,
                "n_reviews": 1,
            }
        },
        {"$sort": {"avg_score": -1, "product_id": 1}},
    ]
