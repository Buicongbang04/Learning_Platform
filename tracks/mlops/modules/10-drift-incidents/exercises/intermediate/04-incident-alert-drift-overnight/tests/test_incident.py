import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
DAYS = pd.date_range("2026-02-02", periods=21, freq="D")
CUTOVER = DAYS[20]
PER_DAY = 1000
UNIT = 60


def logs(seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for day in DAYS:
        distance = rng.lognormal(0.8, 0.7, PER_DAY)
        fare = 3 + 2.5 * distance + rng.normal(0, 1, PER_DAY)
        base_value = 240 + 150 * distance + rng.normal(0, 60, PER_DAY)
        rows.append(pd.DataFrame({"day": day, "trip_distance": distance, "fare_amount": fare, "duration_value": base_value}))
    truth = pd.concat(rows, ignore_index=True)
    shown = truth.copy()
    after = shown["day"] >= CUTOVER
    shown.loc[after, "duration_value"] = shown.loc[after, "duration_value"] / UNIT
    return truth, shown


def split(df):
    return df[df["day"] < DAYS[14]], df[df["day"] >= CUTOVER]


def test_symptom_is_reproduced_on_the_raw_logs():
    mod = ex.module("monitor_pipeline.py")
    _, shown = logs()
    reference, current = split(shown)
    assert mod.drifted_columns(reference, current) == ["duration_value"]
    assert mod.drift_scores(reference, current)["duration_value"] > 1.0
    assert mod.drift_scores(reference, current)["trip_distance"] < 0.05


def test_change_point_day_finds_the_day_it_started():
    mod = ex.module("monitor_pipeline.py")
    _, shown = logs()
    assert mod.change_point_day(shown, "duration_value") == CUTOVER
    assert mod.change_point_day(shown, "fare_amount") is None
    assert mod.change_point_day(shown, "trip_distance") is None


def test_level_by_period_returns_the_two_medians():
    mod = ex.module("monitor_pipeline.py")
    _, shown = logs()
    before, after = mod.level_by_period(shown, "duration_value", CUTOVER)
    assert before == pytest.approx(shown.loc[shown["day"] < CUTOVER, "duration_value"].median())
    assert after == pytest.approx(shown.loc[shown["day"] >= CUTOVER, "duration_value"].median())
    assert isinstance(before, float) and isinstance(after, float)


def test_adjust_from_restores_values_without_touching_anything_else():
    mod = ex.module("monitor_pipeline.py")
    truth, shown = logs()
    fixed = mod.adjust_from(shown, "duration_value", CUTOVER, lambda s: s * 60)
    assert len(fixed) == len(shown)
    np.testing.assert_allclose(fixed["duration_value"].to_numpy(), truth["duration_value"].to_numpy(), rtol=1e-9)
    pd.testing.assert_frame_equal(fixed.drop(columns="duration_value"), shown.drop(columns="duration_value"))
    assert shown["duration_value"].iloc[-1] < truth["duration_value"].iloc[-1]


def test_after_adjust_from_no_column_drifts():
    mod = ex.module("monitor_pipeline.py")
    _, shown = logs()
    fixed = mod.adjust_from(shown, "duration_value", CUTOVER, lambda s: s * 60)
    reference, current = split(fixed)
    assert mod.drifted_columns(reference, current) == []
    assert max(mod.drift_scores(reference, current).values()) < 0.1


def test_range_guard_with_bounds_from_the_reference():
    mod = ex.module("monitor_pipeline.py")
    _, shown = logs()
    reference, current = split(shown)
    low, high = reference["duration_value"].quantile([0.001, 0.999])
    assert mod.range_guard(reference, "duration_value", low, high) is True
    assert mod.range_guard(current, "duration_value", low, high) is False
    healed = mod.adjust_from(shown, "duration_value", CUTOVER, lambda s: s * 60)
    assert mod.range_guard(split(healed)[1], "duration_value", low, high) is True


def test_range_guard_threshold_is_inclusive():
    mod = ex.module("monitor_pipeline.py")
    df = pd.DataFrame({"x": [1.0] * 95 + [999.0] * 5})
    assert mod.range_guard(df, "x", 0, 10, max_outside=0.05) is True
    assert mod.range_guard(df, "x", 0, 10, max_outside=0.04) is False
