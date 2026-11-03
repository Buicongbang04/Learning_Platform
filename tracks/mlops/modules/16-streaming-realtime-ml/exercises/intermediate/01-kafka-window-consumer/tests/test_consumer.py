import json
import random
from datetime import datetime, timezone

import pytest
import tlcstream

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
WINDOW = 900
LATENESS = 180


@pytest.fixture(scope="module")
def consumer():
    return ex.module("consumer.py")


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def produce(bootstrap, topic, events):
    from kafka import KafkaProducer

    producer = KafkaProducer(bootstrap_servers=bootstrap, value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                             key_serializer=lambda k: str(k).encode("utf-8"))
    try:
        for event in events:
            producer.send(topic, key=event["zone_id"], value=event)
        producer.flush(timeout=30)
    finally:
        producer.close()


def real_stream(seed=0):
    trips = tlcstream.zone_trips()
    events = [
        {"event_id": r.event_id, "zone_id": int(r.zone_id), "pickup_at": iso(int(r.pickup.timestamp())), "fare": float(r.fare)}
        for r in trips.itertuples()
    ]
    rng = random.Random(seed)
    stream = tlcstream.shuffle_bounded(events, max_shift=30, seed=seed)
    for _ in range(12):
        i = rng.randrange(len(stream) - 500)
        stream.insert(i + 400, stream.pop(i))
    for _ in range(30):
        i = rng.randrange(len(stream) - 25)
        stream.insert(i + rng.randrange(1, 25), dict(stream[i]))
    return stream


def reference(events):
    seen, mark, late, dups, windows = set(), None, 0, 0, {}
    for e in events:
        if e["event_id"] in seen:
            dups += 1
            continue
        seen.add(e["event_id"])
        ts = int(datetime.strptime(e["pickup_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
        start = ts // WINDOW * WINDOW
        if mark is not None and start + WINDOW <= mark:
            late += 1
        else:
            w = windows.setdefault((e["zone_id"], start), [0, 0.0])
            w[0] += 1
            w[1] += e["fare"]
        mark = ts - LATENESS if mark is None else max(mark, ts - LATENESS)
    return windows, late, dups


def run_topic(consumer, events):
    with mlopskit.kafka_topic() as topic:
        bootstrap = mlopskit.require_kafka()
        produce(bootstrap, topic, events)
        return consumer.consume_windows(bootstrap, topic, window_s=WINDOW, lateness_s=LATENESS, idle_ms=3000)


def test_small_stream_on_real_topic(consumer):
    t0 = 1_551_772_800
    events = [
        {"event_id": "a", "zone_id": 1, "pickup_at": iso(t0 + 10), "fare": 10.0},
        {"event_id": "b", "zone_id": 2, "pickup_at": iso(t0 + 20), "fare": 4.0},
        {"event_id": "c", "zone_id": 1, "pickup_at": iso(t0 + 1_000), "fare": 6.0},
        {"event_id": "d", "zone_id": 1, "pickup_at": iso(t0 + 890), "fare": 2.0},
        {"event_id": "a", "zone_id": 1, "pickup_at": iso(t0 + 10), "fare": 10.0},
        {"event_id": "e", "zone_id": 2, "pickup_at": iso(t0 + 1_200), "fare": 8.0},
        {"event_id": "f", "zone_id": 1, "pickup_at": iso(t0 + 300), "fare": 50.0},
        {"event_id": "g", "zone_id": 2, "pickup_at": iso(t0 + 1_900), "fare": 3.0},
    ]
    got = run_topic(consumer, events)
    assert got["consumed"] == 8
    assert got["duplicates"] == 1
    assert got["late"] == 1
    rows = {(r["zone_id"], r["window_start"]): r for r in got["windows"]}
    assert set(rows) == {(1, t0), (2, t0), (1, t0 + 900), (2, t0 + 900), (2, t0 + 1_800)}
    assert rows[(1, t0)]["trips"] == 2 and rows[(1, t0)]["avg_fare"] == pytest.approx(6.0)
    assert rows[(2, t0 + 900)]["trips"] == 1 and rows[(2, t0 + 900)]["avg_fare"] == pytest.approx(8.0)
    assert all(r["window_end"] == r["window_start"] + WINDOW for r in got["windows"])
    order = [(r["window_end"], r["zone_id"]) for r in got["windows"]]
    assert order[:2] == [(t0 + 900, 1), (t0 + 900, 2)]


def test_real_trips_replayed_out_of_order(consumer):
    events = real_stream()
    windows, late, dups = reference(events)
    got = run_topic(consumer, events)
    assert got["consumed"] == len(events)
    assert got["duplicates"] == dups == 30
    assert got["late"] == late and late >= 12
    rows = {(r["zone_id"], r["window_start"]): r for r in got["windows"]}
    assert len(rows) == len(got["windows"]) == len(windows)
    for key, (trips, total) in windows.items():
        row = rows[key]
        assert row["trips"] == trips
        assert row["avg_fare"] == pytest.approx(total / trips)
    assert set(rows[next(iter(rows))]) == {"zone_id", "window_start", "window_end", "trips", "avg_fare"}
