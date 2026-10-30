import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
FLAG_COLUMNS = ["cnt", "hours", "iqr", "zscore", "demand_drop", "sensor_error"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("bike_outliers.ipynb")


def test_iqr_flags(nb):
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 100.0, -50.0])
    out = nb.iqr_flags(s)
    assert out.dtype == bool and list(out.index) == list(s.index)
    assert out[out].index.tolist() == [8, 9]
    # Q1 = 3.25, Q3 = 7.75, IQR = 4.5; k = 3 -> biên trên 21.25: 20 giữ, 25 bị đánh dấu
    assert nb.iqr_flags(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 20.0, 25.0]), k=3).tolist() == [False] * 9 + [True]


def test_zscore_flags(nb):
    s = pd.Series([10.0] * 20 + [100.0])
    out = nb.zscore_flags(s)
    assert out.dtype == bool
    assert out[out].index.tolist() == [20]
    assert not nb.zscore_flags(s, z=5.0).any()                 # z của điểm 100 là 4.36 (std mẫu)


def test_zscore_masked_by_outlier(nb):
    # một điểm cực lớn làm std phình ra, điểm lớn thứ hai thoát (masking)
    s = pd.Series([10.0, 11.0, 9.0, 10.0, 12.0, 8.0, 10.0, 60.0, 400.0])
    assert nb.zscore_flags(s, z=2.0)[nb.zscore_flags(s, z=2.0)].index.tolist() == [8]
    assert nb.iqr_flags(s)[nb.iqr_flags(s)].index.tolist() == [7, 8]


def small_day():
    dates = pd.date_range("2012-01-01", periods=9, freq="D")
    return pd.DataFrame({
        "dteday": dates,
        "cnt": [100, 110, 90, 105, 5, 95, 100, 120, 98],
        "hum": [0.5, 0.6, 0.0, 0.7, 0.9, 0.4, 0.5, 0.6, 0.55],
    })


def small_hour():
    dates = pd.date_range("2012-01-01", periods=9, freq="D")
    hours = [24, 24, 24, 24, 3, 24, 24, 24, 23]
    return pd.DataFrame({"dteday": np.repeat(dates, hours), "hr": np.concatenate([np.arange(h) for h in hours])})


def test_demand_ratio(nb):
    out = nb.demand_ratio(small_day(), window=5)
    assert list(out.index) == list(pd.date_range("2012-01-01", periods=9, freq="D"))
    # ngày 5 (cnt 5): median của 5 ngày quanh nó [90, 105, 5, 95, 100] là 95
    assert out.iloc[4] == pytest.approx(5 / 95)
    # ngày đầu: cửa sổ giữa cắt còn 3 ngày [100, 110, 90], đủ min_periods = 3
    assert out.iloc[0] == pytest.approx(100 / 100)
    assert out.iloc[-1] == pytest.approx(98 / 100)              # ngày cuối: [100, 120, 98] -> median 100

def test_hours_recorded(nb):
    out = nb.hours_recorded(small_hour())
    assert out.tolist() == [24, 24, 24, 24, 3, 24, 24, 24, 23]


def test_flag_days(nb):
    out = nb.flag_days(small_day(), small_hour(), window=5)
    assert list(out.columns) == FLAG_COLUMNS
    assert out.index.name == "dteday"
    assert out.loc["2012-01-05", "demand_drop"] and out["demand_drop"].sum() == 1
    assert out.loc["2012-01-03", "sensor_error"] and out["sensor_error"].sum() == 1
    assert out.loc["2012-01-05", "hours"] == 3
    assert out["iqr"].sum() == 1 and out.loc["2012-01-05", "iqr"]
    for col in ["iqr", "zscore", "demand_drop", "sensor_error"]:
        assert out[col].dtype == bool


def test_flag_days_does_not_mutate_input(nb):
    day, hour = small_day(), small_hour()
    before_day, before_hour = day.copy(), hour.copy()
    nb.flag_days(day, hour, window=5)
    pd.testing.assert_frame_equal(day, before_day)
    pd.testing.assert_frame_equal(hour, before_hour)


@pytest.fixture(scope="module")
def real():
    path = ex.dataset("bike-sharing-uci")
    return (pd.read_csv(path / "day.csv", parse_dates=["dteday"]), pd.read_csv(path / "hour.csv", parse_dates=["dteday"]))


def test_real_daily_flags(nb, real):
    day, hour = real
    out = nb.flag_days(day, hour)
    assert out[["iqr", "zscore", "demand_drop", "sensor_error"]].sum().tolist() == [0, 0, 17, 1]
    assert out["sensor_error"].idxmax() == pd.Timestamp("2011-03-10")
    assert out.loc["2012-10-29", "hours"] == 1 and out.loc["2012-10-29", "cnt"] == 22
    assert nb.demand_ratio(day).idxmin() == pd.Timestamp("2012-10-29")


def test_real_hourly_iqr(nb, real):
    _, hour = real
    flags = nb.iqr_flags(hour["cnt"])
    assert flags.sum() == 505
    assert hour.loc[flags, "hr"].isin([7, 8, 9, 16, 17, 18, 19]).mean() == pytest.approx(0.861, abs=0.001)
