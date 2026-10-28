import pytest

from testkit import Exercise

ex = Exercise(__file__)

# event_time tính bằng giây kể từ mốc 0 cho dễ đọc
EVENTS = [
    {"order_id": "o1", "customer_state": "SP", "amount": 100.0, "event_time": 5},
    {"order_id": "o2", "customer_state": "RJ", "amount": 50.5, "event_time": 30},
    {"order_id": "o3", "customer_state": "SP", "amount": 20.25, "event_time": 59},
    {"order_id": "o4", "customer_state": "SP", "amount": 10.0, "event_time": 60},
    {"order_id": "o5", "customer_state": "RJ", "amount": 1.1, "event_time": 125},
    {"order_id": "o6", "customer_state": "MG", "amount": 2.2, "event_time": 130},
    {"order_id": "o7", "customer_state": "RJ", "amount": 3.3, "event_time": 179},
]


@pytest.fixture(scope="module")
def w():
    return ex.module("windows.py")


def test_tumbling_window_start(w):
    assert w.tumbling_window_start(0, 60) == 0
    assert w.tumbling_window_start(59, 60) == 0
    assert w.tumbling_window_start(60, 60) == 60
    assert w.tumbling_window_start(125, 60) == 120
    with pytest.raises(ValueError):
        w.tumbling_window_start(10, 0)


def test_hopping_window_starts(w):
    assert w.hopping_window_starts(725, 300, 60) == [480, 540, 600, 660, 720]
    assert w.hopping_window_starts(60, 120, 60) == [0, 60]
    assert w.hopping_window_starts(10, 120, 60) == [0]
    assert w.hopping_window_starts(125, 60, 60) == [120]


def test_hopping_invalid(w):
    with pytest.raises(ValueError):
        w.hopping_window_starts(10, 60, 120)
    with pytest.raises(ValueError):
        w.hopping_window_starts(10, 60, 0)


def test_tumbling_aggregate(w):
    result = w.tumbling_aggregate(EVENTS, 60)
    assert result == [
        {"window_start": 0, "window_end": 60, "key": "RJ", "count": 1, "sum": 50.5},
        {"window_start": 0, "window_end": 60, "key": "SP", "count": 2, "sum": 120.25},
        {"window_start": 60, "window_end": 120, "key": "SP", "count": 1, "sum": 10.0},
        {"window_start": 120, "window_end": 180, "key": "MG", "count": 1, "sum": 2.2},
        {"window_start": 120, "window_end": 180, "key": "RJ", "count": 2, "sum": 4.4},
    ]


def test_tumbling_aggregate_is_order_independent(w):
    assert w.tumbling_aggregate(list(reversed(EVENTS)), 60) == w.tumbling_aggregate(EVENTS, 60)


def test_tumbling_custom_fields(w):
    events = [{"seller": "s1", "price": 1, "event_time": 0}, {"seller": "s1", "price": 2, "event_time": 1}]
    assert w.tumbling_aggregate(events, 10, key_field="seller", value_field="price") == [
        {"window_start": 0, "window_end": 10, "key": "s1", "count": 2, "sum": 3.0}
    ]


def test_hopping_aggregate(w):
    result = w.hopping_aggregate(EVENTS, 120, 60)
    sp = [r for r in result if r["key"] == "SP"]
    assert sp == [
        {"window_start": 0, "window_end": 120, "key": "SP", "count": 3, "sum": 130.25},
        {"window_start": 60, "window_end": 180, "key": "SP", "count": 1, "sum": 10.0},
    ]
    rj = [(r["window_start"], r["count"], r["sum"]) for r in result if r["key"] == "RJ"]
    assert rj == [(0, 1, 50.5), (60, 2, 4.4), (120, 2, 4.4)]
    total_counts = sum(r["count"] for r in result)
    assert total_counts == 11  # 3 event có event_time < 60 thuộc 1 window, 4 event còn lại thuộc 2


def test_hopping_equals_tumbling_when_advance_is_size(w):
    assert w.hopping_aggregate(EVENTS, 60, 60) == w.tumbling_aggregate(EVENTS, 60)
