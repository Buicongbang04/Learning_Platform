"""Lời giải: CRUD review Olist trên MongoDB."""

from __future__ import annotations

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

COLLECTION = "reviews"


def load_reviews(db: Database, reviews: list[dict]) -> int:
    coll = db[COLLECTION]
    for review in reviews:
        doc = {k: v for k, v in review.items() if k != "review_id"}
        doc["_id"] = review["review_id"]
        coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)
    return coll.count_documents({})


def low_score_reviews(db: Database, max_score: int = 2) -> list[dict]:
    cursor = (
        db[COLLECTION]
        .find({"score": {"$lte": max_score}}, {"_id": 1, "order_id": 1, "score": 1})
        .sort([("score", ASCENDING), ("_id", ASCENDING)])
    )
    return [{"review_id": d["_id"], "order_id": d["order_id"], "score": d["score"]} for d in cursor]


def reviews_for_product(db: Database, product_id: str, limit: int = 10) -> list[dict]:
    cursor = (
        db[COLLECTION]
        .find({"product_id": product_id})
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return list(cursor)


def answer_review(db: Database, review_id: str, answer: str) -> bool:
    result = db[COLLECTION].update_one(
        {"_id": review_id},
        {"$set": {"answer": answer, "answered": True}, "$inc": {"answer_count": 1}},
    )
    return result.matched_count == 1


def create_indexes(db: Database) -> str:
    return db[COLLECTION].create_index([("product_id", ASCENDING), ("created_at", DESCENDING)])
