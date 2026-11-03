import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture
def report():
    return ex.module("skew.py").skew_report


@pytest.fixture
def frames():
    rng = np.random.default_rng(0)
    n = 1000
    offline = pd.DataFrame(
        {
            "trip_id": np.arange(n),
            "avg_speed": rng.uniform(5, 40, n),
            "zone_id": rng.integers(1, 200, n).astype("float64"),
            "is_night": rng.integers(0, 2, n),
            "borough": rng.choice(["Manhattan", "Queens", "Bronx"], n),
        }
    )
    online = offline.copy()
    online["avg_speed"] = online["avg_speed"].round(1)
    online.loc[online.index[:50], "zone_id"] = np.nan
    online = online.drop(index=range(990, 1000)).assign(debug_flag=1)
    return offline, online


def test_identical_frames_report_nothing(report, frames):
    offline, _ = frames
    assert report(offline, offline.sample(frac=1, random_state=1), key="trip_id") == []


def test_rounding_is_value_mismatch_with_max_diff(report, frames):
    offline, online = frames
    item = next(i for i in report(offline, online, key="trip_id") if i["column"] == "avg_speed")
    assert item["kind"] == "value_mismatch"
    assert 0.5 < item["mismatch_rate"] < 1.0
    assert 0 < item["max_abs_diff"] <= 0.05 + 1e-9


def test_default_filled_with_null_is_null_mismatch(report, frames):
    offline, online = frames
    item = next(i for i in report(offline, online, key="trip_id") if i["column"] == "zone_id")
    assert item["kind"] == "null_mismatch"
    assert item["mismatch_rate"] == pytest.approx(50 / 990)


def test_missing_column_and_row_coverage(report, frames):
    offline, online = frames
    by_col = {i["column"]: i for i in report(offline, online, key="trip_id")}
    assert by_col["debug_flag"]["kind"] == "missing_column"
    assert by_col["__rows__"]["kind"] == "row_coverage"
    assert by_col["__rows__"]["mismatch_rate"] == pytest.approx(10 / 1000)
    assert "is_night" not in by_col and "borough" not in by_col


def test_sorted_by_mismatch_rate_then_name(report, frames):
    offline, online = frames
    items = report(offline, online, key="trip_id")
    keys = [(-i["mismatch_rate"], i["column"]) for i in items]
    assert keys == sorted(keys)
    assert items[0]["column"] == "debug_flag"


def test_tolerance_hides_tiny_float_noise(report, frames):
    offline, _ = frames
    noisy = offline.assign(avg_speed=offline["avg_speed"] * (1 + 1e-9))
    assert report(offline, noisy, key="trip_id") == []
    assert [i["column"] for i in report(offline, noisy, key="trip_id", rtol=1e-12, atol=0.0)] == ["avg_speed"]


def test_nan_equal_nan_is_not_a_mismatch(report):
    a = pd.DataFrame({"k": [1, 2, 3], "x": [1.0, np.nan, 3.0]})
    b = pd.DataFrame({"k": [3, 2, 1], "x": [3.0, np.nan, 1.0]})
    assert report(a, b, key="k") == []


def test_categorical_mismatch_has_no_max_diff(report):
    a = pd.DataFrame({"k": [1, 2], "c": ["x", "y"]})
    b = pd.DataFrame({"k": [1, 2], "c": ["x", "Y"]})
    assert report(a, b, key="k") == [{"column": "c", "kind": "value_mismatch", "mismatch_rate": 0.5, "max_abs_diff": None}]


def test_inputs_are_not_mutated(report, frames):
    offline, online = frames
    before = (offline.copy(), online.copy())
    report(offline, online, key="trip_id")
    pd.testing.assert_frame_equal(offline, before[0])
    pd.testing.assert_frame_equal(online, before[1])
