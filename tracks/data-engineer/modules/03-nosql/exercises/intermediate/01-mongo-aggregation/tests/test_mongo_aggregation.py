from datetime import datetime

import mongomock
import pytest

from testkit import Exercise

ex = Exercise(__file__)

ORDERS = [
    {"order_id": "o1", "customer_id": "c1", "customer_state": "SP", "order_status": "delivered",
     "purchased_at": datetime(2018, 1, 10, 9, 30)},
    {"order_id": "o2", "customer_id": "c2", "customer_state": "RJ", "order_status": "delivered",
     "purchased_at": datetime(2018, 1, 20, 14, 0)},
    {"order_id": "o3", "customer_id": "c1", "customer_state": "SP", "order_status": "canceled",
     "purchased_at": datetime(2018, 2, 3, 8, 0)},
    {"order_id": "o4", "customer_id": "c3", "customer_state": "MG", "order_status": "delivered",
     "purchased_at": datetime(2018, 2, 15, 18, 45)},
    {"order_id": "o5", "customer_id": "c4", "customer_state": "SP", "order_status": "created",
     "purchased_at": datetime(2018, 3, 1, 7, 0)},
]
ITEMS = [
    {"order_id": "o1", "order_item_id": 2, "product_id": "p2", "seller_id": "s1", "price": 50.0, "freight_value": 5.5},
    {"order_id": "o1", "order_item_id": 1, "product_id": "p1", "seller_id": "s1", "price": 100.0, "freight_value": 10.25},
    {"order_id": "o2", "order_item_id": 1, "product_id": "p3", "seller_id": "s2", "price": 30.0, "freight_value": 7.0},
    {"order_id": "o3", "order_item_id": 1, "product_id": "p1", "seller_id": "s1", "price": 100.0, "freight_value": 10.0},
    {"order_id": "o4", "order_item_id": 1, "product_id": "p1", "seller_id": "s3", "price": 90.0, "freight_value": 12.0},
    {"order_id": "o4", "order_item_id": 2, "product_id": "p9", "seller_id": "s3", "price": 15.0, "freight_value": 0.0},
]
PRODUCTS = [
    {"product_id": "p1", "category": "housewares"},
    {"product_id": "p2", "category": "toys"},
    {"product_id": "p3", "category": "toys"},
]
REVIEWS = [
    {"_id": "r1", "product_id": "p1", "score": 5},
    {"_id": "r2", "product_id": "p1", "score": 4},
    {"_id": "r3", "product_id": "p1", "score": 3},
    {"_id": "r4", "product_id": "p2", "score": 5},
    {"_id": "r5", "product_id": "p2", "score": 3},
    {"_id": "r6", "product_id": "p3", "score": 1},
    {"_id": "r7", "product_id": "p3", "score": 5},
    {"_id": "r8", "product_id": "p9", "score": 2},
]


@pytest.fixture
def mod():
    return ex.module("pipelines.py")


@pytest.fixture
def db(mod):
    database = mongomock.MongoClient().olist
    database.orders.insert_many(mod.build_order_documents(ORDERS, ITEMS, PRODUCTS))
    database.reviews.insert_many([dict(r) for r in REVIEWS])
    database.products.insert_many([{"_id": p["product_id"], "category": p["category"]} for p in PRODUCTS])
    return database


def rounded(rows, *fields):
    out = []
    for row in rows:
        row = dict(row)
        for f in fields:
            row[f] = round(row[f], 2)
        out.append(row)
    return out


def test_build_order_documents(mod):
    docs = {d["_id"]: d for d in mod.build_order_documents(ORDERS, ITEMS, PRODUCTS)}
    assert set(docs) == {"o1", "o2", "o3", "o4", "o5"}
    o1 = docs["o1"]
    assert o1["customer"] == {"id": "c1", "state": "SP"}
    assert o1["status"] == "delivered"
    assert o1["purchased_at"] == datetime(2018, 1, 10, 9, 30)
    assert o1["items"] == [
        {"product_id": "p1", "seller_id": "s1", "category": "housewares", "price": 100.0, "freight": 10.25},
        {"product_id": "p2", "seller_id": "s1", "category": "toys", "price": 50.0, "freight": 5.5},
    ]
    assert o1["total"] == 165.75
    assert docs["o4"]["items"][1]["category"] is None
    assert docs["o5"]["items"] == [] and docs["o5"]["total"] == 0.0


def test_revenue_by_category(mod, db):
    pipeline = mod.revenue_by_category_pipeline()
    assert "$match" in pipeline[0], "Đặt $match ở stage đầu để lọc sớm và dùng được index"
    result = rounded(db.orders.aggregate(pipeline), "revenue")
    assert result == [
        {"category": "housewares", "revenue": 190.0, "items": 2},
        {"category": "toys", "revenue": 80.0, "items": 2},
        {"category": None, "revenue": 15.0, "items": 1},
    ]
    canceled = list(db.orders.aggregate(mod.revenue_by_category_pipeline("canceled")))
    assert rounded(canceled, "revenue") == [{"category": "housewares", "revenue": 100.0, "items": 1}]


def test_monthly_orders(mod, db):
    result = rounded(db.orders.aggregate(mod.monthly_orders_pipeline()), "gmv")
    assert result == [
        {"month": "2018-01", "orders": 2, "gmv": 202.75},
        {"month": "2018-02", "orders": 2, "gmv": 227.0},
        {"month": "2018-03", "orders": 1, "gmv": 0.0},
    ]


def test_product_rating(mod, db):
    result = rounded(db.reviews.aggregate(mod.product_rating_pipeline()), "avg_score")
    assert result == [
        {"product_id": "p1", "category": "housewares", "avg_score": 4.0, "n_reviews": 3},
        {"product_id": "p2", "category": "toys", "avg_score": 4.0, "n_reviews": 2},
        {"product_id": "p3", "category": "toys", "avg_score": 3.0, "n_reviews": 2},
    ]
    top = list(db.reviews.aggregate(mod.product_rating_pipeline(min_reviews=3)))
    assert [r["product_id"] for r in top] == ["p1"]
