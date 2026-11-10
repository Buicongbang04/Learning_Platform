import random

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BASE = 1_762_214_400
SIZE = 900
LATENESS = 120


@pytest.fixture(scope="module")
def win():
    return ex.module("windows.py")


def ev(event_id, key, ts, value=1.0):
    return {"event_id": event_id, "key": key, "ts": ts, "value": value}


def run(win, events, size=SIZE, lateness=LATENESS):
    agg = win.WindowAggregator(size, lateness)
    emitted = []
    for i, event in enumerate(events):
        for row in agg.add(dict(event)):
            emitted.append((i, row))
    for row in agg.flush():
        emitted.append((len(events), row))
    return agg, emitted


def generate(seed):
    rng = random.Random(seed)
    events = []
    for n in range(700):
        ts = BASE + rng.randrange(0, 7_200)
        delay = rng.choice([0] * 6 + [30, 60, 100, 200, 400] + [1_500])
        events.append((ts + delay, ev(f"e{n}", rng.choice("abc"), ts, round(rng.uniform(5, 60), 2))))
    arrivals = sorted(events, key=lambda pair: pair[0])
    stream = [e for _, e in arrivals]
    for _ in range(40):
        stream.insert(rng.randrange(len(stream)), dict(rng.choice(stream)))
    return stream


def reference(events, size, lateness):
    seen, wm, late, dups = set(), None, 0, 0
    windows, emit_at, marks = {}, {}, []
    for i, e in enumerate(events):
        if e["event_id"] in seen:
            dups += 1
            marks.append(wm)
            continue
        seen.add(e["event_id"])
        start = (e["ts"] // size) * size
        end = start + size
        if wm is not None and end <= wm:
            late += 1
        else:
            w = windows.setdefault((e["key"], start), {"count": 0, "total": 0.0, "born": i})
            w["count"] += 1
            w["total"] += e["value"]
        wm = e["ts"] - lateness if wm is None else max(wm, e["ts"] - lateness)
        marks.append(wm)
    for (key, start), w in windows.items():
        end = start + size
        emit_at[(key, start)] = next((j for j in range(w["born"], len(events)) if marks[j] is not None and marks[j] >= end), len(events))
    return windows, emit_at, late, dups, wm


def test_tumbling_start(win):
    assert win.tumbling_start(BASE, SIZE) == BASE
    assert win.tumbling_start(BASE + 899, SIZE) == BASE
    assert win.tumbling_start(BASE + 900, SIZE) == BASE + 900
    assert win.tumbling_start(125, 60) == 120


def test_sliding_windows(win):
    assert win.sliding_windows(125, 60, 20) == [(80, 140), (100, 160), (120, 180)]
    assert win.sliding_windows(120, 60, 20) == [(80, 140), (100, 160), (120, 180)]
    assert win.sliding_windows(119, 60, 20) == [(60, 120), (80, 140), (100, 160)]
    assert win.sliding_windows(BASE + 10, 900, 300) == [(BASE - 600, BASE + 300), (BASE - 300, BASE + 600), (BASE, BASE + 900)]
    assert win.sliding_windows(7, 10, 10) == [(0, 10)]


def test_session_windows(win):
    assert win.session_windows([], 30) == []
    assert win.session_windows([100, 110, 135, 200, 229, 300], 30) == [(100, 165), (200, 259), (300, 330)]
    assert win.session_windows([200, 100, 129], 30) == [(100, 159), (200, 230)]
    assert win.session_windows([100, 130], 30) == [(100, 130), (130, 160)]


def test_window_closes_when_watermark_passes_end(win):
    agg = win.WindowAggregator(60, 10)
    assert agg.add(ev("1", "a", 5, 2.0)) == []
    assert agg.watermark == -5
    assert agg.add(ev("2", "a", 50, 3.0)) == []
    assert agg.add(ev("3", "b", 69, 1.0)) == []
    rows = agg.add(ev("4", "b", 70, 4.0))
    assert rows == [{"key": "a", "window_start": 0, "window_end": 60, "count": 2, "total": 5.0}]
    assert agg.watermark == 60
    assert agg.flush() == [{"key": "b", "window_start": 60, "window_end": 120, "count": 2, "total": 5.0}]
    assert agg.flush() == []


def test_late_within_and_beyond_lateness(win):
    agg = win.WindowAggregator(60, 30)
    agg.add(ev("1", "a", 10, 1.0))
    agg.add(ev("2", "a", 85, 1.0))
    assert agg.add(ev("3", "a", 40, 1.0)) == []
    assert agg.late == 0
    rows = agg.add(ev("4", "a", 95, 1.0))
    assert rows == [{"key": "a", "window_start": 0, "window_end": 60, "count": 2, "total": 2.0}]
    assert agg.add(ev("5", "a", 59, 7.0)) == []
    assert agg.late == 1
    assert agg.flush() == [{"key": "a", "window_start": 60, "window_end": 120, "count": 2, "total": 2.0}]


def test_event_exactly_at_closed_boundary_is_late(win):
    agg = win.WindowAggregator(60, 0)
    agg.add(ev("1", "a", 0, 1.0))
    assert agg.add(ev("2", "a", 60, 1.0)) == [{"key": "a", "window_start": 0, "window_end": 60, "count": 1, "total": 1.0}]
    assert agg.add(ev("3", "a", 59, 5.0)) == []
    assert agg.late == 1
    assert agg.flush() == [{"key": "a", "window_start": 60, "window_end": 120, "count": 1, "total": 1.0}]


def test_duplicates_counted_once(win):
    agg = win.WindowAggregator(60, 0)
    agg.add(ev("x", "a", 1, 5.0))
    agg.add(ev("x", "a", 1, 5.0))
    agg.add(ev("y", "a", 2, 1.0))
    agg.add(ev("y", "a", 2, 1.0))
    agg.add(ev("new", "a", 70, 1.0))
    agg.add(ev("old", "a", 3, 1.0))
    agg.add(ev("old", "a", 3, 1.0))
    assert agg.duplicates == 3
    assert agg.late == 1
    assert agg.flush() == [{"key": "a", "window_start": 60, "window_end": 120, "count": 1, "total": 1.0}]


def test_rows_emitted_in_end_then_key_order(win):
    agg = win.WindowAggregator(10, 25)
    for i, (key, ts) in enumerate([("b", 1), ("a", 2), ("c", 15), ("a", 12)]):
        assert agg.add(ev(str(i), key, ts)) == []
    rows = agg.add(ev("z", "a", 45))
    assert [(r["window_end"], r["key"]) for r in rows] == [(10, "a"), (10, "b"), (20, "a"), (20, "c")]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_matches_reference_on_disordered_stream(win, seed):
    events = generate(seed)
    agg, emitted = run(win, events)
    windows, emit_at, late, dups, wm = reference(events, SIZE, LATENESS)
    assert agg.late == late and agg.duplicates == dups and agg.watermark == wm
    got = {(r["key"], r["window_start"]): (i, r) for i, r in emitted}
    assert len(got) == len(emitted) == len(windows)
    for key, w in windows.items():
        i, row = got[key]
        assert row["window_end"] == key[1] + SIZE
        assert row["count"] == w["count"]
        assert row["total"] == pytest.approx(w["total"])
        assert i == emit_at[key]
    assert late > 0 and dups > 0
