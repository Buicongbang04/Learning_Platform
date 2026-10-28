from datetime import datetime

import mongomock
import pytest

from testkit import Exercise

ex = Exercise(__file__)


def sample_reviews():
    return [
        {"review_id": "r1", "order_id": "o1", "product_id": "p1", "score": 5,
         "comment": "otimo", "created_at": datetime(2018, 3, 1, 10)},
        {"review_id": "r2", "order_id": "o2", "product_id": "p1", "score": 1,
         "comment": "nao chegou", "created_at": datetime(2018, 3, 5, 9)},
        {"review_id": "r3", "order_id": "o3", "product_id": "p2", "score": 2,
         "comment": "atrasou", "created_at": datetime(2018, 2, 1, 8)},
        {"review_id": "r4", "order_id": "o4", "product_id": "p1", "score": 4,
         "comment": "bom", "created_at": datetime(2018, 4, 2, 12)},
        {"review_id": "r0", "order_id": "o5", "product_id": "p3", "score": 1,
         "comment": "ruim", "created_at": datetime(2018, 1, 2, 12)},
    ]


@pytest.fixture
def db():
    return mongomock.MongoClient().olist


@pytest.fixture
def reviews():
    return ex.module("reviews.py")


def test_load_is_idempotent(db, reviews):
    assert reviews.load_reviews(db, sample_reviews()) == 5
    assert reviews.load_reviews(db, sample_reviews()) == 5
    doc = db.reviews.find_one({"_id": "r1"})
    assert doc is not None and "review_id" not in doc
    changed = sample_reviews()
    changed[0]["score"] = 3
    assert reviews.load_reviews(db, changed[:1]) == 5
    assert db.reviews.find_one({"_id": "r1"})["score"] == 3


def test_low_score_reviews(db, reviews):
    reviews.load_reviews(db, sample_reviews())
    result = reviews.low_score_reviews(db)
    assert result == [
        {"review_id": "r0", "order_id": "o5", "score": 1},
        {"review_id": "r2", "order_id": "o2", "score": 1},
        {"review_id": "r3", "order_id": "o3", "score": 2},
    ]
    assert [r["review_id"] for r in reviews.low_score_reviews(db, max_score=1)] == ["r0", "r2"]


def test_reviews_for_product(db, reviews):
    reviews.load_reviews(db, sample_reviews())
    result = reviews.reviews_for_product(db, "p1")
    assert [r["_id"] for r in result] == ["r4", "r2", "r1"]
    assert result[0]["comment"] == "bom"
    assert len(reviews.reviews_for_product(db, "p1", limit=2)) == 2
    assert reviews.reviews_for_product(db, "nope") == []


def test_answer_review(db, reviews):
    reviews.load_reviews(db, sample_reviews())
    assert reviews.answer_review(db, "r2", "Sentimos muito") is True
    assert reviews.answer_review(db, "r2", "Reenviado") is True
    doc = db.reviews.find_one({"_id": "r2"})
    assert doc["answered"] is True
    assert doc["answer"] == "Reenviado"
    assert doc["answer_count"] == 2
    assert doc["comment"] == "nao chegou"
    assert reviews.answer_review(db, "missing", "x") is False


def test_create_indexes(db, reviews):
    name = reviews.create_indexes(db)
    info = db.reviews.index_information()
    assert name in info
    assert info[name]["key"] == [("product_id", 1), ("created_at", -1)]
