import zlib

import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def p():
    return ex.module("partitioning.py")


def test_partition_for_key_is_crc32(p):
    for key in [b"order-1", b"order-2", b"e481f51cbdc54678b7cc49136f2d6af7"]:
        assert p.partition_for(key, 6) == zlib.crc32(key) % 6


def test_partition_for_same_key_same_partition(p):
    assert len({p.partition_for(b"abc", 12) for _ in range(20)}) == 1


def test_partition_for_keyless_round_robin(p):
    assert [p.partition_for(None, 3, c) for c in range(6)] == [0, 1, 2, 0, 1, 2]


def test_partition_for_invalid(p):
    with pytest.raises(ValueError):
        p.partition_for(b"x", 0)


def test_assign_keeps_order_per_key(p):
    events = []
    for i in range(5):
        for order in ["o1", "o2", "o3", "o4"]:
            events.append({"order_id": order, "seq": i})
    result = p.assign(events, 3)
    assert sorted(result) == [0, 1, 2]
    assert sum(len(v) for v in result.values()) == len(events)
    for order in ["o1", "o2", "o3", "o4"]:
        part = zlib.crc32(order.encode()) % 3
        seqs = [e["seq"] for e in result[part] if e["order_id"] == order]
        assert seqs == [0, 1, 2, 3, 4]
        others = [e for q, evs in result.items() if q != part for e in evs if e["order_id"] == order]
        assert others == []


def test_assign_keyless_round_robin(p):
    events = [{"seq": i} for i in range(4)]
    result = p.assign(events, 2)
    assert [e["seq"] for e in result[0]] == [0, 2]
    assert [e["seq"] for e in result[1]] == [1, 3]


def test_assign_empty_partitions_present(p):
    assert p.assign([], 4) == {0: [], 1: [], 2: [], 3: []}


def test_range_assign_uneven(p):
    result = p.range_assign([5, 0, 1, 2, 3, 4, 6], ["c2", "c1", "c3"])
    assert result == {"c1": [0, 1, 2], "c2": [3, 4], "c3": [5, 6]}


def test_range_assign_more_consumers_than_partitions(p):
    result = p.range_assign([0, 1], ["a", "b", "c"])
    assert result == {"a": [0], "b": [1], "c": []}


def test_range_assign_no_consumer(p):
    with pytest.raises(ValueError):
        p.range_assign([0, 1], [])


def test_consumer_lag(p):
    end = {0: 100, 1: 50, 2: 10}
    committed = {0: 90, 1: None}
    assert p.consumer_lag(end, committed) == {0: 10, 1: 50, 2: 10}
    assert p.total_lag(end, committed) == 70


def test_consumer_lag_never_negative(p):
    assert p.consumer_lag({0: 5}, {0: 7}) == {0: 0}
