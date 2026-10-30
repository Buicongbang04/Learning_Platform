import numpy as np
import pandas as pd
import pytest
from scipy import stats

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("bike_tests.ipynb")


def test_to_business_units(nb):
    day = pd.DataFrame({"temp": [0.5, 1.0], "hum": [0.62, 0.0], "windspeed": [0.1, 0.5], "cnt": [10, 20]})
    before = day.copy()
    out = nb.to_business_units(day)
    assert out["temp_c"].tolist() == pytest.approx([20.5, 41.0])
    assert out["hum_pct"].tolist() == pytest.approx([62.0, 0.0])
    assert out["wind_kmh"].tolist() == pytest.approx([6.7, 33.5])
    assert {"temp", "hum", "windspeed", "cnt"} <= set(out.columns)
    pd.testing.assert_frame_equal(day, before)


def test_corr_with_ci_matches_scipy(nb):
    rng = np.random.default_rng(7)
    x = rng.normal(size=200)
    y = 0.4 * x + rng.normal(size=200)
    out = nb.corr_with_ci(pd.Series(x), pd.Series(y))
    ref = stats.pearsonr(x, y)
    ci = ref.confidence_interval()
    assert out["n"] == 200
    assert out["r"] == pytest.approx(ref.statistic)
    assert out["p"] == pytest.approx(ref.pvalue, rel=1e-6)
    assert out["ci_low"] == pytest.approx(ci.low, abs=1e-9)
    assert out["ci_high"] == pytest.approx(ci.high, abs=1e-9)


def test_corr_with_ci_drops_missing_and_alpha(nb):
    x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, np.nan, 7.0, 8.0])
    y = pd.Series([2.0, 1.0, 4.0, 3.0, 6.0, 5.0, np.nan, 9.0])
    out = nb.corr_with_ci(x, y)
    assert out["n"] == 6
    assert out["r"] == pytest.approx(x.corr(y))
    wide = nb.corr_with_ci(x, y, alpha=0.01)
    assert wide["ci_low"] < out["ci_low"] < out["r"] < out["ci_high"] < wide["ci_high"]


def test_welch_compare_matches_scipy(nb):
    a = [1.0, 2.0, 4.0, 7.0, 11.0]
    b = [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 30.0]
    out = nb.welch_compare(a, b)
    ref = stats.ttest_ind(a, b, equal_var=False)
    ci = ref.confidence_interval()
    assert out["diff"] == pytest.approx(np.mean(a) - np.mean(b))
    assert out["mean_a"] == pytest.approx(5.0)
    assert out["p"] == pytest.approx(ref.pvalue)
    assert out["ci_low"] == pytest.approx(ci.low)
    assert out["ci_high"] == pytest.approx(ci.high)
    assert (out["n_a"], out["n_b"]) == (5, 8)


def test_welch_compare_alpha(nb):
    a, b = [1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0, 9.0]
    out90, out99 = nb.welch_compare(a, b, alpha=0.10), nb.welch_compare(a, b, alpha=0.01)
    assert out99["ci_low"] < out90["ci_low"] and out99["ci_high"] > out90["ci_high"]


def test_matched_holiday_gap(nb):
    day = pd.DataFrame({
        "dteday": pd.to_datetime(["2011-01-03", "2011-01-04", "2011-01-05", "2011-01-17",
                                  "2011-07-04", "2011-07-05", "2011-07-06", "2011-07-09"]),
        "yr": [0] * 8, "mnth": [1, 1, 1, 1, 7, 7, 7, 7],
        "holiday": [0, 0, 0, 1, 1, 0, 0, 0], "workingday": [1, 1, 1, 0, 0, 1, 1, 0],
        "cnt": [100, 200, 300, 150, 900, 500, 700, 5000],
    })
    before = day.copy()
    gap = nb.matched_holiday_gap(day, "cnt")
    assert gap.name == "gap"
    # tháng 1: 150 - mean(100, 200, 300) = -50; tháng 7: 900 - mean(500, 700) = 300 (bỏ cuối tuần 9/7)
    assert list(gap.index) == list(pd.to_datetime(["2011-01-17", "2011-07-04"]))
    assert gap.tolist() == pytest.approx([-50.0, 300.0])
    pd.testing.assert_frame_equal(day, before)


@pytest.fixture(scope="module")
def real_raw():
    return pd.read_csv(ex.dataset("bike-sharing-uci") / "day.csv", parse_dates=["dteday"])


def test_real_correlations(nb, real_raw):
    real_day = nb.to_business_units(real_raw)
    temp = nb.corr_with_ci(real_day["temp_c"], real_day["cnt"])
    assert temp["n"] == 731
    assert temp["r"] == pytest.approx(0.6275, abs=1e-4)
    assert temp["ci_low"] == pytest.approx(0.5814, abs=1e-4)
    hum = nb.corr_with_ci(real_day["hum_pct"], real_day["cnt"])
    assert hum["r"] == pytest.approx(-0.1007, abs=1e-4)
    assert hum["p"] == pytest.approx(0.00645, abs=1e-4)


def test_real_holiday(nb, real_raw):
    real_day = nb.to_business_units(real_raw)
    holiday, work = real_day[real_day.holiday == 1], real_day[real_day.workingday == 1]
    raw = nb.welch_compare(holiday["cnt"], work["cnt"])
    assert (raw["n_a"], raw["n_b"]) == (21, 500)
    assert raw["diff"] == pytest.approx(-849.82, abs=0.01)
    assert raw["p"] == pytest.approx(0.0826, abs=1e-3)
    gap = nb.matched_holiday_gap(real_day, "cnt")
    assert len(gap) == 21
    assert gap.mean() == pytest.approx(-594.8, abs=0.1)
    assert (nb.matched_holiday_gap(real_day, "casual") > 0).all()
