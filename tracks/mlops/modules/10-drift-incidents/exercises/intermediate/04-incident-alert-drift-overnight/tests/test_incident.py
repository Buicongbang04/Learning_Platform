import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
DAYS = pd.date_range("2026-02-02", periods=21, freq="D")
CUTOVER = DAYS[20]
PER_DAY = 1000


def logs(seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for day in DAYS:
        distance = rng.lognormal(0.8, 0.7, PER_DAY)
        fare = 3 + 2.5 * distance + rng.normal(0, 1, PER_DAY)
        seconds = 240 + 150 * distance + rng.normal(0, 60, PER_DAY)
        rows.append(pd.DataFrame({"day": day, "trip_distance": distance, "fare_amount": fare, "trip_time": seconds}))
    truth = pd.concat(rows, ignore_index=True)
    shown = truth.copy()
    after = shown["day"] >= CUTOVER
    shown.loc[after, "trip_time"] = shown.loc[after, "trip_time"] / 60
    return truth, shown


def split(df):
    return df[df["day"] < DAYS[14]], df[df["day"] >= CUTOVER]


def test_symptom_is_reproduced_on_the_raw_logs():
    mod = ex.module("monitor_pipeline.py")
    _, shown = logs()
    reference, current = split(shown)
    assert mod.drifted_columns(reference, current) == ["trip_time"]
    assert mod.drift_scores(reference, current)["trip_time"] > 1.0
    assert mod.drift_scores(reference, current)["trip_distance"] < 0.05


def test_change_point_day_finds_the_day_it_started():
    mod = ex.module("monitor_pipeline.py")
    _, shown = logs()
    assert mod.change_point_day(shown, "trip_time") == CUTOVER
    assert mod.change_point_day(shown, "fare_amount") is None
    assert mod.change_point_day(shown, "trip_distance") is None


def test_median_ratio_is_a_whole_number():
    mod = ex.module("monitor_pipeline.py")
    _, shown = logs()
    ratio = mod.median_ratio(shown, "trip_time", CUTOVER)
    assert isinstance(ratio, float) and ratio == float(int(ratio))
    assert ratio == 60.0


def test_adjust_from_restores_values_without_touching_anything_else():
    mod = ex.module("monitor_pipeline.py")
    truth, shown = logs()
    fixed = mod.adjust_from(shown, "trip_time", CUTOVER, 60.0)
    assert len(fixed) == len(shown)
    np.testing.assert_allclose(fixed["trip_time"].to_numpy(), truth["trip_time"].to_numpy(), rtol=1e-9)
    pd.testing.assert_frame_equal(fixed.drop(columns="trip_time"), shown.drop(columns="trip_time"))
    assert shown["trip_time"].iloc[-1] < 60


def test_after_adjust_from_no_column_drifts():
    mod = ex.module("monitor_pipeline.py")
    _, shown = logs()
    fixed = mod.adjust_from(shown, "trip_time", CUTOVER, mod.median_ratio(shown, "trip_time", CUTOVER))
    reference, current = split(fixed)
    assert mod.drifted_columns(reference, current) == []
    assert max(mod.drift_scores(reference, current).values()) < 0.1


def test_range_guard_stops_the_bad_batch_before_monitoring_sees_it():
    mod = ex.module("monitor_pipeline.py")
    truth, shown = logs()
    reference, current = split(shown)
    assert mod.range_guard(reference, "trip_time", 30, 7200) is True
    assert mod.range_guard(current, "trip_time", 30, 7200) is False
    healed = mod.adjust_from(shown, "trip_time", CUTOVER, 60.0)
    assert mod.range_guard(split(healed)[1], "trip_time", 30, 7200) is True


def test_range_guard_threshold_is_inclusive():
    mod = ex.module("monitor_pipeline.py")
    df = pd.DataFrame({"x": [1.0] * 95 + [999.0] * 5})
    assert mod.range_guard(df, "x", 0, 10, max_outside=0.05) is True
    assert mod.range_guard(df, "x", 0, 10, max_outside=0.04) is False
