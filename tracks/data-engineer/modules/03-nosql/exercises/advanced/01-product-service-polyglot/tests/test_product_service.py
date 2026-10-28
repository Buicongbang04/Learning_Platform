from datetime import datetime

import fakeredis
import mongomock
import pytest

import testkit
from testkit import Exercise, use_solution

if use_solution():
    pytest.skip("Bài advanced không có lời giải chạy được; xem SOLUTION.md", allow_module_level=True)

ex = Exercise(__file__)

PRODUCTS = [
    {"_id": "p1", "category": "housewares", "price": 29.9},
    {"_id": "p2", "category": "toys", "price": 59.0},
    {"_id": "p3", "category": "toys", "price": 15.5},
    {"_id": "p4", "category": "books", "price": 40.0},
]


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def review(rid, pid, score):
    return {"review_id": rid, "product_id": pid, "score": score, "created_at": datetime(2018, 5, 1, 10)}


def make_backends(kind):
    if kind == "offline":
        db = mongomock.MongoClient().ex03_adv01
        r = fakeredis.FakeRedis(decode_responses=True)
        return db, r, lambda: None
    ex.require_service("mongo")
    ex.require_service("redis")
    import pymongo
    import redis

    client = pymongo.MongoClient(testkit.MONGO_URI, serverSelectionTimeoutMS=2000)
    client.drop_database("ex03_adv01")
    db = client.ex03_adv01
    r = redis.Redis.from_url(testkit.REDIS_URL, db=15, decode_responses=True)
    # Không xoá dữ liệu không phải của bài này: db 15 có sẵn key là có thể của dự án khác.
    if r.dbsize() > 0:
        client.close()
        pytest.skip("Redis db 15 đang có dữ liệu (có thể của dự án khác), bỏ qua bản chạy live")

    def cleanup():
        client.drop_database("ex03_adv01")
        r.flushdb()
        client.close()

    return db, r, cleanup


@pytest.fixture(params=["offline", "live"])
def env(request):
    db, r, cleanup = make_backends(request.param)
    db.products.insert_many([dict(p) for p in PRODUCTS])
    clock = Clock()
    mod = ex.module("service.py")
    svc = mod.ProductService(db, r, clock=clock, min_reviews=3, rate_limit=5, rate_window=60)
    yield svc, db, r, clock
    cleanup()


def test_get_product_cache(env):
    svc, db, r, _ = env
    first = svc.get_product("p1")
    assert first["category"] == "housewares"
    # Sửa thẳng MongoDB mà không qua service: lần đọc sau vẫn phải lấy từ cache
    db.products.update_one({"_id": "p1"}, {"$set": {"category": "changed"}})
    second = svc.get_product("p1")
    assert second == first
    assert 0 < r.ttl("product:p1") <= 360
    assert svc.get_product("nope") is None


def test_add_review_idempotent_and_fresh(env):
    svc, db, _, _ = env
    assert svc.get_product("p2").get("review_count", 0) == 0
    assert svc.add_review(review("r1", "p2", 5)) is True
    assert svc.add_review(review("r1", "p2", 5)) is False
    assert svc.add_review(review("r2", "p2", 2)) is True
    product = svc.get_product("p2")
    assert product["review_count"] == 2
    assert product["avg_score"] == pytest.approx(3.5)
    assert db.reviews.count_documents({}) == 2


def test_top_rated_and_rebuild(env):
    svc, _, r, _ = env
    scores = {"p1": [5, 4, 5], "p2": [3, 3, 4, 2], "p3": [5, 5], "p4": [4, 4, 4]}
    n = 0
    for pid, values in scores.items():
        for s in values:
            n += 1
            svc.add_review(review(f"r{n}", pid, s))
    expected = [("p1", pytest.approx(14 / 3)), ("p4", pytest.approx(4.0)), ("p2", pytest.approx(3.0))]
    assert svc.top_rated(10) == expected  # p3 chỉ có 2 review
    assert svc.top_rated(1) == expected[:1]
    r.delete("top_rated")
    assert svc.top_rated(10) == expected


def test_recently_viewed(env):
    svc, _, _, _ = env
    for pid in ["p1", "p2", "p3", "p1"]:
        svc.record_view("u1", pid)
    assert svc.recently_viewed("u1") == ["p1", "p3", "p2"]
    for i in range(15):
        svc.record_view("u2", f"x{i}")
    viewed = svc.recently_viewed("u2")
    assert len(viewed) == 10 and viewed[0] == "x14" and viewed[-1] == "x5"
    assert svc.recently_viewed("nobody") == []


def test_rate_limit(env):
    svc, _, _, clock = env
    results = []
    for _ in range(7):
        results.append(svc.allow_request("api-key-1"))
        clock.t += 1
    assert results == [True] * 5 + [False] * 2
    assert svc.allow_request("api-key-2") is True
    clock.t += 60
    assert svc.allow_request("api-key-1") is True
