import pytest

from testkit import Exercise

ex = Exercise(__file__)


def ev(t, key="SP", amount=10.0):
    return {"event_time": t, "key": key, "amount": amount}


@pytest.fixture(scope="module")
def wm():
    return ex.module("watermark.py")


def test_watermark_property(wm):
    p = wm.TumblingWindowProcessor(60, allowed_lateness=30)
    assert p.watermark is None
    p.process(ev(100))
    assert p.watermark == 70
    p.process(ev(80))  # event lệch thứ tự không kéo watermark lùi
    assert p.watermark == 70


def test_no_emit_until_watermark_passes_window_end(wm):
    p = wm.TumblingWindowProcessor(60, allowed_lateness=0)
    assert p.process(ev(10)) == []
    assert p.process(ev(59, amount=5)) == []
    out = p.process(ev(60))  # watermark = 60 >= end của [0, 60)
    assert out == [{"window_start": 0, "window_end": 60, "key": "SP", "count": 2, "total": 15.0}]


def test_out_of_order_within_lateness_is_counted(wm):
    p = wm.TumblingWindowProcessor(60, allowed_lateness=30)
    assert p.process(ev(50)) == []
    assert p.process(ev(70)) == []      # watermark 40
    assert p.process(ev(20)) == []      # trễ nhưng window [0,60) chưa đóng
    out = p.process(ev(95))             # watermark 65 >= 60
    assert out == [{"window_start": 0, "window_end": 60, "key": "SP", "count": 2, "total": 20.0}]
    assert p.late_events == []


def test_late_event_goes_to_side_output(wm):
    p = wm.TumblingWindowProcessor(60, allowed_lateness=10)
    p.process(ev(30))
    p.process(ev(130))                  # watermark 120: đóng [0,60) và [60,120)
    late = ev(45, amount=99)
    assert p.process(late) == []
    assert p.late_events == [late]
    rest = p.flush()
    assert rest == [{"window_start": 120, "window_end": 180, "key": "SP", "count": 1, "total": 10.0}]


def test_each_window_emitted_once_and_sorted(wm):
    p = wm.TumblingWindowProcessor(60, allowed_lateness=100)
    assert p.process(ev(1, "SP")) == []
    assert p.process(ev(2, "RJ", 1.5)) == []
    assert p.process(ev(61, "MG")) == []
    out = p.process(ev(250, "SP"))  # watermark 150 đóng [0,60) và [60,120)
    assert [(r["window_start"], r["key"]) for r in out] == [(0, "RJ"), (0, "SP"), (60, "MG")]
    assert p.process(ev(251, "SP")) == []


def test_flush_emits_remaining(wm):
    p = wm.TumblingWindowProcessor(60, allowed_lateness=100)
    p.process(ev(10))
    p.process(ev(70, "RJ"))
    assert p.flush() == [
        {"window_start": 0, "window_end": 60, "key": "SP", "count": 1, "total": 10.0},
        {"window_start": 60, "window_end": 120, "key": "RJ", "count": 1, "total": 10.0},
    ]
    assert p.flush() == []


def test_run_tradeoff_lateness(wm):
    stream = [ev(10), ev(65), ev(130), ev(50), ev(200), ev(115)]
    strict, late_strict = wm.run(stream, 60, 0)
    relaxed, late_relaxed = wm.run(stream, 60, 120)
    assert [e["event_time"] for e in late_strict] == [50, 115]
    assert late_relaxed == []
    assert sum(r["count"] for r in strict) == 4
    assert sum(r["count"] for r in relaxed) == 6
    assert [(r["window_start"], r["count"]) for r in relaxed] == [(0, 2), (60, 2), (120, 1), (180, 1)]
