import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
DAYS = pd.date_range("2026-01-05", periods=70, freq="D")


def seasonal_series():
    weekly = np.array([16.0, 16.0, 16.0, 16.0, 17.0, 12.0, 11.0])
    jitter = np.array([-0.2, 0.0, 0.2, 0.1, -0.1])[(np.arange(len(DAYS)) // 7) % 5]
    pred = pd.Series(weekly[DAYS.day_of_week] + jitter, index=DAYS)
    fallback = pd.Series(0.01 + jitter / 100, index=DAYS)
    return pred, fallback


def test_labeled_mae_only_uses_matured_labels():
    mod = ex.module("proxy.py")
    df = pd.DataFrame({
        "ts": pd.to_datetime(["2026-03-01", "2026-03-02", "2026-03-04", "2026-03-04"]),
        "pred": [10.0, 10.0, 10.0, 10.0],
        "label": [12.0, 13.0, 100.0, 100.0],
    })
    assert mod.labeled_mae(df, pd.Timestamp("2026-03-05"), 2) == pytest.approx(2.5)
    assert mod.labeled_mae(df, pd.Timestamp("2026-03-05"), 4) == pytest.approx(2.0)
    assert mod.labeled_mae(df, pd.Timestamp("2026-03-05"), 5) is None
    assert mod.labeled_mae(df, pd.Timestamp("2026-03-03"), 2) == pytest.approx(2.0)


def test_seasonal_baseline_uses_same_weekday():
    mod = ex.module("proxy.py")
    daily = pd.Series(np.arange(len(DAYS), dtype=float), index=DAYS)
    day = DAYS[30]
    mean, std = mod.seasonal_baseline(daily, day, weeks=4)
    expected = [30 - 7, 30 - 14, 30 - 21, 30 - 28]
    assert mean == pytest.approx(np.mean(expected))
    assert std == pytest.approx(np.std(expected, ddof=1))


def test_seasonal_baseline_skips_missing_days_and_needs_two():
    mod = ex.module("proxy.py")
    daily = pd.Series(np.arange(len(DAYS), dtype=float), index=DAYS)
    mean, _ = mod.seasonal_baseline(daily, DAYS[16], weeks=4)
    assert mean == pytest.approx(np.mean([9, 2]))
    with pytest.raises(ValueError):
        mod.seasonal_baseline(daily, DAYS[10], weeks=4)


def test_quiet_weekend_drop_is_not_an_alert():
    mod = ex.module("proxy.py")
    pred, fallback = seasonal_series()
    for day in DAYS[35:]:
        assert mod.proxy_alerts(pred, fallback, day) == [], day


def test_naive_day_over_day_would_alarm_but_seasonal_does_not():
    mod = ex.module("proxy.py")
    pred, fallback = seasonal_series()
    saturday = next(d for d in DAYS[35:] if d.day_of_week == 5)
    assert abs(pred[saturday] - pred[saturday - pd.Timedelta(days=1)]) > 3
    assert mod.proxy_alerts(pred, fallback, saturday) == []


def test_prediction_shift_alerts_on_pred_mean():
    mod = ex.module("proxy.py")
    pred, fallback = seasonal_series()
    day = DAYS[-3]
    pred[day] += 4.0
    assert mod.proxy_alerts(pred, fallback, day) == ["pred_mean"]


def test_fallback_jump_alerts_on_fallback():
    mod = ex.module("proxy.py")
    pred, fallback = seasonal_series()
    day = DAYS[-2]
    fallback[day] = 0.06
    assert mod.proxy_alerts(pred, fallback, day) == ["fallback"]


def test_both_signals_in_documented_order():
    mod = ex.module("proxy.py")
    pred, fallback = seasonal_series()
    day = DAYS[-1]
    pred[day] -= 5.0
    fallback[day] = 0.08
    assert mod.proxy_alerts(pred, fallback, day) == ["pred_mean", "fallback"]
