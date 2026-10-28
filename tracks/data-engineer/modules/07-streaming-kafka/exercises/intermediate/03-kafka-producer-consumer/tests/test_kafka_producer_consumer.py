import uuid

import pytest

import testkit
from testkit import Exercise

ex = Exercise(__file__)

ORDERS = ["o-aaa", "o-bbb", "o-ccc"]
STATUSES = ["created", "approved", "shipped"]
EVENTS = [
    {"event_id": f"{o}-{s}", "order_id": o, "status": s, "amount": 10.0 * (i + 1), "city": "são paulo"}
    for s in STATUSES
    for i, o in enumerate(ORDERS)
]


@pytest.fixture(scope="module")
def kio():
    return ex.module("kafka_io.py")


# ---------- Phần offline: không cần Kafka ----------

def test_encode_decode(kio):
    data = kio.encode_value(EVENTS[0])
    assert isinstance(data, bytes)
    assert "são paulo" in data.decode("utf-8")
    assert b" " not in data.replace("são paulo".encode(), b"")
    assert kio.decode_value(data) == EVENTS[0]


def test_encode_key(kio):
    assert kio.encode_key("o-aaa") == b"o-aaa"
    assert kio.encode_key(None) is None


def test_producer_config_is_durable(kio):
    cfg = kio.producer_config()
    assert cfg["acks"] in ("all", -1)
    assert cfg["retries"] > 0
    assert cfg["max_in_flight_requests_per_connection"] == 1
    assert cfg["key_serializer"]("k") == b"k"
    assert kio.decode_value(cfg["value_serializer"]({"a": 1})) == {"a": 1}


def test_consumer_config_at_least_once(kio):
    cfg = kio.consumer_config("g1")
    assert cfg["group_id"] == "g1"
    assert cfg["enable_auto_commit"] is False
    assert cfg["auto_offset_reset"] == "earliest"
    assert cfg["key_deserializer"](b"o-aaa") == "o-aaa"
    assert cfg["value_deserializer"](b'{"a":1}') == {"a": 1}


# ---------- Phần cần Kafka thật ----------

@pytest.fixture(scope="module")
def topic():
    ex.require_service("kafka")
    from kafka.admin import KafkaAdminClient, NewTopic

    name = f"test.orders.{uuid.uuid4().hex[:8]}"
    admin = KafkaAdminClient(bootstrap_servers=testkit.KAFKA_BOOTSTRAP)
    admin.create_topics([NewTopic(name=name, num_partitions=3, replication_factor=1)])
    yield name
    try:
        admin.delete_topics([name])
    finally:
        admin.close()


@pytest.fixture(scope="module")
def produced(kio, topic):
    producer = kio.make_producer(testkit.KAFKA_BOOTSTRAP)
    try:
        return kio.produce_events(producer, topic, EVENTS)
    finally:
        producer.close()


def test_produce_returns_positions(produced):
    assert len(produced) == len(EVENTS)
    by_order = {}
    for event, (partition, offset) in zip(EVENTS, produced):
        by_order.setdefault(event["order_id"], []).append((partition, offset))
    for positions in by_order.values():
        assert len({p for p, _ in positions}) == 1, "Cùng order_id phải vào cùng partition"
        offsets = [o for _, o in positions]
        assert offsets == sorted(offsets)


def test_consume_all_in_order_then_committed(kio, topic, produced):
    group = f"g-{uuid.uuid4().hex[:8]}"
    records = kio.consume_events(testkit.KAFKA_BOOTSTRAP, topic, group, max_records=len(EVENTS))
    assert sorted(r["value"]["event_id"] for r in records) == sorted(e["event_id"] for e in EVENTS)
    for order in ORDERS:
        mine = [r for r in records if r["key"] == order]
        assert [r["value"]["status"] for r in sorted(mine, key=lambda r: r["offset"])] == STATUSES

    again = kio.consume_events(testkit.KAFKA_BOOTSTRAP, topic, group, max_records=1, timeout_s=5)
    assert again == [], "Offset đã commit nên cùng group không đọc lại"


def test_new_group_replays(kio, topic, produced):
    group = f"g-{uuid.uuid4().hex[:8]}"
    records = kio.consume_events(testkit.KAFKA_BOOTSTRAP, topic, group, max_records=len(EVENTS))
    assert len(records) == len(EVENTS)
