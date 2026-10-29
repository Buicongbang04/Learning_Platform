import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

Y = np.array([5.0, 7.0, 6.0, 9.0, 8.0, 10.0, 11.0])


@pytest.fixture(scope="module")
def bl():
    return ex.module("baselines.py")


def test_naive(bl):
    out = bl.naive(Y, 3)
    assert isinstance(out, np.ndarray)
    np.testing.assert_allclose(out, [11.0, 11.0, 11.0])


def test_mean_forecast(bl):
    np.testing.assert_allclose(bl.mean_forecast(Y, 2), [Y.mean()] * 2)


def test_mean_forecast_window(bl):
    np.testing.assert_allclose(bl.mean_forecast(Y, 2, window=3), [29 / 3] * 2)


def test_drift_is_line_through_first_and_last(bl):
    slope = (11.0 - 5.0) / 6
    np.testing.assert_allclose(bl.drift(Y, 3), [11 + slope, 11 + 2 * slope, 11 + 3 * slope])


def test_drift_exact_on_linear_series(bl):
    y = 3.0 + 2.0 * np.arange(20)
    np.testing.assert_allclose(bl.drift(y, 5), 3.0 + 2.0 * np.arange(20, 25))


def test_seasonal_naive_repeats_last_season(bl):
    y = np.arange(1.0, 15.0)            # 2 tuần: 1..14
    np.testing.assert_allclose(bl.seasonal_naive(y, 10, m=7), [8, 9, 10, 11, 12, 13, 14, 8, 9, 10])


def test_seasonal_naive_aligns_phase_for_any_horizon(bl):
    rng = np.random.default_rng(0)
    week = np.array([30.0, 28, 27, 25, 22, 10, 12])
    y = np.tile(week, 6)[:-3]          # kết thúc giữa tuần
    out = bl.seasonal_naive(y, 17, m=7)
    expected = np.tile(week, 6)[-3:].tolist() + np.tile(week, 3).tolist()
    np.testing.assert_allclose(out, expected[:17])


def test_seasonal_naive_needs_full_season(bl):
    with pytest.raises(ValueError):
        bl.seasonal_naive(np.ones(5), 3, m=7)


def test_accepts_series(bl):
    s = pd.Series(Y, index=pd.date_range("2018-01-01", periods=len(Y)))
    np.testing.assert_allclose(bl.naive(s, 1), [11.0])
    np.testing.assert_allclose(bl.seasonal_naive(s, 2, m=3), [8.0, 10.0])


def test_seasonal_naive_beats_naive_on_weekly_pattern(bl):
    rng = np.random.default_rng(2)
    week = np.array([30.0, 28, 27, 25, 22, 10, 12])
    y = np.tile(week, 12) + rng.normal(0, 1, 84)
    train, test = y[:-14], y[-14:]
    err_naive = np.mean(np.abs(test - bl.naive(train, 14)))
    err_snaive = np.mean(np.abs(test - bl.seasonal_naive(train, 14, m=7)))
    assert err_snaive < err_naive / 3
