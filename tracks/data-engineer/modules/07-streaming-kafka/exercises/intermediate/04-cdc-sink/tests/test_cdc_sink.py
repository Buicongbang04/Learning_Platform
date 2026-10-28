import sqlite3

import pytest
from testkit import Exercise

ex = Exercise(__file__)
TOPIC = "olist_cdc.public.orders"


@pytest.fixture
def sink():
    m = ex.module("cdc_sink.py")
    con = sqlite3.connect(":memory:")
    m.initialize(con)
    yield m, con
    con.close()


def event(order_id="o1", status="created", amount=15000, op="c"):
    return {"op": op, "after": {"order_id": order_id, "status": status, "amount_cents": amount}}


def apply(sink, offset, value, partition=0, order_id="o1", topic=TOPIC):
    m, con = sink
    return m.apply_record(con, topic, partition, offset, {"order_id": order_id}, value)


def orders(sink):
    return sink[1].execute("SELECT * FROM orders ORDER BY order_id").fetchall()


def test_snapshot_update_delete_tombstone(sink):
    assert apply(sink, 0, event(op="r")) is True
    assert orders(sink) == [("o1", "created", 15000)]
    assert apply(sink, 1, event(status="delivered", amount=12000, op="u")) is True
    assert orders(sink) == [("o1", "delivered", 12000)]
    assert apply(sink, 2, {"op": "d", "before": {"order_id": "o1"}, "after": None}) is True
    assert apply(sink, 3, None) is True
    assert orders(sink) == []
    assert sink[1].execute("SELECT last_offset FROM checkpoints").fetchall() == [(3,)]


def test_replay_after_crash_and_delete_does_not_resurrect(sink):
    assert apply(sink, 0, event()) is True
    assert apply(sink, 0, event()) is False
    assert apply(sink, 1, {"op": "d", "after": None}) is True
    assert apply(sink, 0, event()) is False
    assert orders(sink) == []


def test_partitions_and_topics_have_independent_offsets(sink):
    assert apply(sink, 50, event()) is True
    assert apply(sink, 0, event("o2"), partition=1, order_id="o2") is True
    assert apply(sink, 0, event("o3"), order_id="o3", topic="other") is True
    assert len(orders(sink)) == 3
    assert sink[1].execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 3


@pytest.mark.parametrize("value", [
    [],
    {"op": []},
    {"op": "truncate"},
    {"op": "u", "after": None},
    event("wrong"),
    event(amount=-1),
    event(amount=True),
    event(amount="15000"),
    event(status="unknown"),
    event(status=[]),
])
def test_invalid_event_keeps_data_and_checkpoint(sink, value):
    apply(sink, 0, event())
    with pytest.raises(ValueError):
        apply(sink, 1, value)
    assert orders(sink) == [("o1", "created", 15000)]
    assert sink[1].execute("SELECT last_offset FROM checkpoints").fetchone()[0] == 0


def test_failure_writing_checkpoint_rolls_back_order(sink):
    con = sink[1]
    con.executescript("""
        CREATE TRIGGER reject_checkpoint BEFORE INSERT ON checkpoints
        BEGIN SELECT RAISE(ABORT, 'injected checkpoint failure'); END;
    """)
    with pytest.raises(sqlite3.IntegrityError):
        apply(sink, 0, event())
    assert orders(sink) == []
    assert con.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 0
