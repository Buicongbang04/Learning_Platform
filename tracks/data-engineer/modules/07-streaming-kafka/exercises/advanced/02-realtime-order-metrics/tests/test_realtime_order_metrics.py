import json

from testkit import Exercise

ex = Exercise(__file__)


def msg(event_id, t, state="SP", status="created", amount=10.0, order_id=None, **extra):
    event = {
        "event_id": event_id,
        "order_id": order_id or f"o-{event_id}",
        "status": status,
        "amount": amount,
        "customer_state": state,
        "event_time": t,
        **extra,
    }
    return json.dumps(event).encode("utf-8")


def make(**kw):
    return ex.module("processor.py").OrderMetricsProcessor(**kw)


def run_all(p, messages):
    out = []
    for m in messages:
        out.extend(p.process(m))
    out.extend(p.flush())
    return out


def test_watermark_none_then_value():
    p = make(window_size=60, allowed_lateness=30)
    assert p.watermark is None
    p.process(msg("a", 100))
    assert p.watermark == 70


def test_basic_metrics_per_state():
    p = make(window_size=60, allowed_lateness=0)
    out = run_all(p, [
        msg("e1", 1, "SP", amount=100),
        msg("e2", 2, "RJ", amount=50.5),
        msg("e3", 30, "SP", amount=20.25),
        msg("e4", 40, "SP", status="canceled", amount=100),
        msg("e5", 45, "SP", status="shipped", amount=999),
        msg("e6", 61, "MG", amount=5),
    ])
    assert out == [
        {"window_start": 0, "window_end": 60, "customer_state": "RJ", "orders": 1, "gmv": 50.5, "canceled": 0},
        {"window_start": 0, "window_end": 60, "customer_state": "SP", "orders": 2, "gmv": 120.25, "canceled": 1},
        {"window_start": 60, "window_end": 120, "customer_state": "MG", "orders": 1, "gmv": 5.0, "canceled": 0},
    ]


def test_emit_only_when_watermark_passes():
    p = make(window_size=60, allowed_lateness=30)
    assert p.process(msg("a", 10)) == []
    assert p.process(msg("b", 80)) == []     # watermark 50 < 60
    out = p.process(msg("c", 95))            # watermark 65
    assert [(r["window_start"], r["orders"]) for r in out] == [(0, 1)]


def test_invalid_messages_go_to_dlq():
    p = make()
    bad = [
        b"not json",
        b"[1,2,3]",
        json.dumps({"event_id": "x"}).encode(),
        msg("y", 10, status="teleported"),
        msg("z", 10, amount=-1),
        msg("w", "yesterday"),
    ]
    for raw in bad:
        assert p.process(raw) == []
    assert [d["raw"] for d in p.dlq] == bad
    assert all(isinstance(d["reason"], str) and d["reason"] for d in p.dlq)
    assert p.flush() == []
    assert p.watermark is None


def test_duplicates_are_dropped():
    p = make(window_size=60, allowed_lateness=0)
    out = run_all(p, [msg("e1", 5, amount=10), msg("e1", 5, amount=10), msg("e2", 6), msg("e1", 7)])
    assert out[0]["orders"] == 2 and out[0]["gmv"] == 20.0
    assert p.duplicates == 2


def test_dedup_memory_has_ttl():
    p = make(window_size=60, allowed_lateness=10_000, dedup_ttl=100)
    p.process(msg("e1", 0))
    p.process(msg("e2", 500))      # e1 hết TTL (0 < 500 - 100)
    p.process(msg("e1", 0))        # bị coi là event mới: đánh đổi của TTL
    assert p.duplicates == 0
    out = p.flush()
    assert out[0]["window_start"] == 0 and out[0]["orders"] == 2


def test_late_events_side_output():
    p = make(window_size=60, allowed_lateness=10)
    p.process(msg("a", 30))
    p.process(msg("b", 200))       # watermark 190
    p.process(msg("c", 50))        # window [0,60) đã đóng
    assert [e["event_id"] for e in p.late] == ["c"]
    assert all(r["orders"] == 1 for r in p.flush())


def test_out_of_order_within_lateness():
    p = make(window_size=60, allowed_lateness=120)
    out = run_all(p, [msg("a", 10), msg("b", 70), msg("c", 130), msg("d", 50), msg("e", 115)])
    assert [(r["window_start"], r["orders"]) for r in out] == [(0, 2), (60, 2), (120, 1)]
    assert p.late == []


def test_stats():
    p = make(window_size=60, allowed_lateness=0)
    run_all(p, [msg("a", 1), msg("a", 1), b"oops", msg("b", 200), msg("c", 5)])
    assert p.stats() == {"emitted_windows": 2, "duplicates": 1, "late": 1, "dlq": 1}
