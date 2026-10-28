import pytest

from testkit import Exercise

ex = Exercise(__file__)

EVENTS = [
    {"event_id": "e1", "order_id": "o1", "status": "created"},
    {"event_id": "e2", "order_id": "o2", "status": "created"},
    {"event_id": "e1", "order_id": "o1", "status": "created"},  # retry của producer
    {"event_id": "e3", "order_id": "o1", "status": "approved"},
    {"order_id": "o9", "status": "created"},  # không có event_id
    {"event_id": "e2", "order_id": "o2", "status": "created"},
    {"event_id": "e1", "order_id": "o1", "status": "created"},
]

PRICES = [
    ("p1", 10.0),
    ("p2", 20.0),
    ("p1", 12.5),
    ("p3", 5.0),
    ("p2", None),  # tombstone: sản phẩm bị gỡ
    ("p1", 11.0),
]


@pytest.fixture(scope="module")
def d():
    return ex.module("dedup.py")


def test_dedup_keeps_first_in_order(d):
    result = d.dedup_events(EVENTS)
    assert [e.get("event_id") for e in result] == ["e1", "e2", "e3", None]


def test_dedup_does_not_mutate_input(d):
    copy = [dict(e) for e in EVENTS]
    d.dedup_events(EVENTS)
    assert EVENTS == copy


def test_dedup_empty(d):
    assert d.dedup_events([]) == []


def test_count_duplicates(d):
    assert d.count_duplicates(EVENTS) == {"e1": 2, "e2": 1}
    assert d.count_duplicates(EVENTS[:2]) == {}


def test_compact_latest_value_and_tombstone(d):
    assert d.compact(PRICES) == {"p1": 11.0, "p3": 5.0}


def test_compact_tombstone_then_recreate(d):
    assert d.compact([("k", 1), ("k", None), ("k", 2)]) == {"k": 2}


def test_compacted_offsets(d):
    assert d.compacted_offsets(PRICES) == [3, 4, 5]
    assert d.compacted_offsets([]) == []
