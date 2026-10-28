import sqlite3

import pytest

from testkit import Exercise

ex = Exercise(__file__)
T = "olist.orders"


def rec(partition, offset, event_id, order_id, status, amount, state, minute):
    return {
        "topic": T,
        "partition": partition,
        "offset": offset,
        "value": {
            "event_id": event_id,
            "order_id": order_id,
            "status": status,
            "amount": amount,
            "customer_state": state,
            "event_time": f"2018-01-02T10:{minute:02d}:00Z",
        },
    }


BATCH1 = [
    rec(0, 0, "e1", "o1", "created", 100.0, "SP", 0),
    rec(1, 0, "e2", "o2", "created", 50.0, "RJ", 1),
    rec(0, 1, "e3", "o1", "approved", 100.0, "SP", 2),
    rec(1, 1, "e4", "o3", "created", 30.5, "RJ", 3),
]
BATCH2 = [
    rec(1, 2, "e5", "o2", "canceled", 50.0, "RJ", 5),
    rec(0, 2, "e3", "o1", "approved", 100.0, "SP", 2),       # trùng event_id do producer retry
    rec(1, 3, "e6", "o3", "approved", 30.5, "RJ", 1),        # cũ hơn trạng thái đang có -> bỏ
    rec(0, 3, "e7", "o4", "created", 20.0, "MG", 6),
]
EXPECTED_GMV = {"SP": 100.0, "RJ": 30.5, "MG": 20.0}


def make_sink():
    mod = ex.module("sink.py")
    s = mod.OrderSink(sqlite3.connect(":memory:"))
    s.init_schema()
    return s


def test_init_schema_idempotent():
    sink = make_sink()
    sink.init_schema()


def test_happy_path():
    sink = make_sink()
    assert sink.process_batch(BATCH1) == 4
    assert sink.order_status("o1")["status"] == "approved"
    assert sink.committed_offsets() == {(T, 0): 2, (T, 1): 2}
    sink.process_batch(BATCH2)
    assert sink.order_status("o2")["status"] == "canceled"
    assert sink.gmv_by_state() == EXPECTED_GMV
    assert sink.committed_offsets() == {(T, 0): 4, (T, 1): 4}


def test_out_of_order_event_does_not_regress():
    sink = make_sink()
    sink.process_batch(BATCH1)
    sink.process_batch(BATCH2)
    o3 = sink.order_status("o3")
    assert o3["status"] == "created"
    assert o3["event_time"] == "2018-01-02T10:03:00Z"


def test_duplicate_event_id_counted_once():
    sink = make_sink()
    sink.process_batch(BATCH1)
    applied = sink.process_batch(BATCH2)
    assert applied == 3  # e3 trùng bị bỏ; e6 vẫn được tính là đã xử lý dù không đổi trạng thái


def test_replay_same_batch_is_noop():
    sink = make_sink()
    sink.process_batch(BATCH1)
    sink.process_batch(BATCH2)
    before = (sink.gmv_by_state(), sink.committed_offsets())
    assert sink.process_batch(BATCH1) == 0
    assert sink.process_batch(BATCH2) == 0
    assert (sink.gmv_by_state(), sink.committed_offsets()) == before


def test_crash_rolls_back_whole_batch():
    sink = make_sink()
    sink.process_batch(BATCH1)
    with pytest.raises(RuntimeError):
        sink.process_batch(BATCH2, fail_after=2)
    assert sink.order_status("o2")["status"] == "created"
    assert sink.order_status("o4") is None
    assert sink.committed_offsets() == {(T, 0): 2, (T, 1): 2}


def test_crash_then_retry_gives_same_result():
    sink = make_sink()
    sink.process_batch(BATCH1)
    with pytest.raises(RuntimeError):
        sink.process_batch(BATCH2, fail_after=3)
    sink.process_batch(BATCH2)
    assert sink.gmv_by_state() == EXPECTED_GMV
    assert sink.committed_offsets() == {(T, 0): 4, (T, 1): 4}


def test_overlapping_batch_after_restart():
    sink = make_sink()
    # consumer restart, seek về offset cũ hơn nên nhận lại một phần dữ liệu đã xử lý
    sink.process_batch(BATCH1 + BATCH2[:1])
    overlap = BATCH1[2:] + BATCH2
    sink.process_batch(overlap)
    assert sink.gmv_by_state() == EXPECTED_GMV


def test_unknown_order():
    sink = make_sink()
    assert sink.order_status("nope") is None
    assert sink.gmv_by_state() == {}
    assert sink.committed_offsets() == {}
