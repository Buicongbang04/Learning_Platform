import json

import fakeredis
import pytest

from testkit import Exercise

ex = Exercise(__file__)


class FakeDB:
    def __init__(self):
        self.rows = {
            "p1": {"product_id": "p1", "category": "housewares", "price": 29.99},
            "p2": {"product_id": "p2", "category": "bed_bath_table", "price": 89.9},
        }
        self.loads = 0

    def load(self, product_id):
        self.loads += 1
        row = self.rows.get(product_id)
        return dict(row) if row else None

    def save(self, product_id, fields):
        self.rows[product_id].update(fields)


@pytest.fixture
def r():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def setup(r):
    mod = ex.module("cache.py")
    db = FakeDB()
    cache = mod.ProductCache(r, db.load, ttl=300, negative_ttl=30)
    return cache, db


def test_key(setup):
    cache, _ = setup
    assert cache.key("abc") == "product:abc"


def test_hit_after_miss(setup, r):
    cache, db = setup
    first = cache.get("p1")
    second = cache.get("p1")
    assert first == second == db.rows["p1"]
    assert db.loads == 1
    assert json.loads(r.get("product:p1"))["price"] == 29.99
    assert 0 < r.ttl("product:p1") <= 300


def test_negative_caching(setup, r):
    cache, db = setup
    assert cache.get("ghost") is None
    assert cache.get("ghost") is None
    assert db.loads == 1
    assert r.get("product:ghost") == "__none__"
    assert 0 < r.ttl("product:ghost") <= 30


def test_invalidate(setup):
    cache, db = setup
    cache.get("p2")
    assert cache.invalidate("p2") is True
    assert cache.invalidate("p2") is False
    cache.get("p2")
    assert db.loads == 2


def test_update_then_get_fresh(setup):
    cache, db = setup
    assert cache.get("p1")["price"] == 29.99
    cache.update("p1", {"price": 19.99}, db.save)
    assert db.rows["p1"]["price"] == 19.99
    assert cache.get("p1")["price"] == 19.99
    assert db.loads == 2


def test_failed_save_keeps_cache(setup, r):
    cache, _ = setup
    cache.get("p1")

    def broken_saver(product_id, fields):
        raise RuntimeError("db down")

    with pytest.raises(RuntimeError):
        cache.update("p1", {"price": 1.0}, broken_saver)
    assert r.exists("product:p1") == 1
