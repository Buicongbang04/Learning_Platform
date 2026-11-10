import importlib.util
import json

import pytest

from testkit import Exercise

ex = Exercise(__file__)
WINDOW = 900
HOLD = 180
REPORTED_AT = 1_551_776_400


@pytest.fixture(scope="module")
def zone_stream():
    return ex.module("zone_stream.py")


@pytest.fixture(scope="module")
def v1():
    spec = importlib.util.spec_from_file_location("zone_stream_v1", ex.fixtures / "zone_stream.v1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def log():
    with (ex.fixtures / "events.jsonl").open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


@pytest.fixture(scope="module")
def expected():
    return json.loads((ex.fixtures / "expected.json").read_text(encoding="utf-8"))


def replay(module, log):
    zs = module.ZoneStream(window_s=WINDOW, hold_s=HOLD)
    rows = []
    for event in log:
        rows.extend(zs.ingest(dict(event)))
    snapshot = {str(z): row for z, row in zs.snapshot().items()}
    rows.extend(zs.flush())
    return rows, snapshot, dict(zs.stats)


def same_rows(got, want):
    keys = ("zone_id", "window_start", "window_end", "trips")
    return len(got) == len(want) and all(
        {k: a[k] for k in keys} == {k: b[k] for k in keys} and a["avg_fare"] == pytest.approx(b["avg_fare"])
        for a, b in zip(got, want)
    )


def lagging(snapshot, want):
    return sorted(z for z, row in want.items() if snapshot.get(z, {}).get("window_end") != row["window_end"])


def test_online_feature_keeps_moving(zone_stream, log, expected):
    _, snapshot, _ = replay(zone_stream, log)
    behind = lagging(snapshot, expected["main"]["snapshot"])
    assert not behind, f"feature của zone {behind} không theo kịp luồng sự kiện"


def test_window_values_match_reference(zone_stream, log, expected):
    rows, _, _ = replay(zone_stream, log)
    assert same_rows(rows, expected["main"]["rows"]), "các cửa sổ phát ra khác kết quả mong đợi trên cùng log"


def test_counters_match_reference(zone_stream, log, expected):
    _, _, stats = replay(zone_stream, log)
    assert stats == expected["main"]["stats"], "bộ đếm khác kết quả mong đợi trên cùng log"


def test_one_device_far_ahead(zone_stream, log, expected):
    extra = expected["extra"]
    broken = log[: extra["position"]] + [extra["event"]] + log[extra["position"]:]
    rows, snapshot, stats = replay(zone_stream, broken)
    ok = not lagging(snapshot, extra["snapshot"]) and same_rows(rows, extra["rows"]) and stats == extra["stats"]
    assert ok, "một sự kiện hỏng làm sai feature của các sự kiện khác"


def test_reported_build_shows_the_symptom(v1, log, expected):
    _, snapshot, stats = replay(v1, log)
    want = expected["main"]["snapshot"]
    assert lagging(snapshot, want) == sorted(want)
    assert all(row["window_end"] <= REPORTED_AT for row in snapshot.values())
    assert all(row["window_end"] >= REPORTED_AT + 2_700 for row in want.values())
    assert stats["skipped"] > len(log) // 3
