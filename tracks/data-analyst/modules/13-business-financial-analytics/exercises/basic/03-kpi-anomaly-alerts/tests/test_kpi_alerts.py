import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("kpi_alerts.ipynb")


def daily(values, start="2024-01-01"):
    return pd.Series(np.asarray(values, dtype=float), index=pd.date_range(start, periods=len(values), freq="D"),
                     name="cnt")


def test_seasonal_baseline_same_weekday_median(nb):
    # 5 tuần: thứ của ngày i có giá trị 100 + i (tuần 1), 200 + i (tuần 2) ...; ngày 0 tuần 3 là 900 (ngoại lệ)
    values = [100 * (w + 1) + d for w in range(5) for d in range(7)]
    values[14] = 900
    y = daily(values)
    before = y.copy()
    out = nb.seasonal_baseline(y, weeks=3)
    pd.testing.assert_series_equal(y, before)
    assert out.name == "baseline"
    assert out.index.equals(y.index)
    assert out.iloc[:21].isna().all()
    # ngày 21 (tuần 4, d = 0): median(300 → 900, 200, 100) = 200; ngày 28: median(400, 900, 200) = 400
    assert out.iloc[21] == pytest.approx(200.0)
    assert out.iloc[28] == pytest.approx(400.0)
    assert out.iloc[30] == pytest.approx(302.0)


def test_robust_score_uses_only_past_days(nb):
    # baseline 100 mọi ngày; y lặp chu kỳ 110, 90, 100, 120, 85; ngày cuối là cú rơi lớn
    n = 40
    cycle = [110.0, 90.0, 100.0, 120.0, 85.0]
    y = daily([cycle[i % 5] for i in range(n - 1)] + [20.0])
    base = daily([100.0] * n)
    out = nb.robust_score(y, base, window=10, min_periods=5)
    assert out.name == "score"
    assert out.iloc[:5].isna().all() and out.iloc[5:].notna().all()
    ratio = np.log(y / base)
    past = ratio.iloc[n - 11:n - 1].to_numpy()
    scale = 1.4826 * np.median(np.abs(past - np.median(past)))
    assert out.iloc[-1] == pytest.approx(np.log(0.2) / scale)
    # ngày 5: cửa sổ chỉ có 5 ngày 0..4 (đủ min_periods)
    window5 = ratio.iloc[:5].to_numpy()
    scale5 = 1.4826 * np.median(np.abs(window5 - np.median(window5)))
    assert out.iloc[5] == pytest.approx(ratio.iloc[5] / scale5)


def test_robust_score_skips_nan_in_window(nb):
    y = daily([100.0, 120.0, 80.0, 110.0, 90.0, 105.0, 95.0, 60.0])
    base = daily([np.nan, np.nan, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
    out = nb.robust_score(y, base, window=7, min_periods=3)
    assert out.iloc[:5].isna().all()       # ngày 2..4 có ratio nhưng chưa đủ 3 giá trị quá khứ
    past = np.log(np.array([80.0, 110.0, 90.0]) / 100)
    scale = 1.4826 * np.median(np.abs(past - np.median(past)))
    assert out.iloc[5] == pytest.approx(np.log(1.05) / scale)


def alert_inputs():
    idx = pd.date_range("2024-03-01", periods=8, freq="D")
    y = pd.Series([50.0, 10.0, 12.0, 100.0, 160.0, 100.0, 30.0, 95.0], index=idx)
    base = pd.Series(100.0, index=idx)
    score = pd.Series([np.nan, -9.0, -5.0, 0.5, 4.5, -1.0, -4.2, 3.9], index=idx)
    return y, base, score


def test_alert_table(nb):
    y, base, score = alert_inputs()
    out = nb.alert_table(y, base, score, threshold=4.0)
    assert list(out.columns) == ["value", "baseline", "score", "direction"]
    assert out.index.name == "date"
    assert list(out.index.day) == [2, 3, 5, 7]
    assert out["direction"].tolist() == ["drop", "drop", "spike", "drop"]
    assert out["value"].tolist() == [10.0, 12.0, 160.0, 30.0]


def test_alert_episodes(nb):
    y, base, score = alert_inputs()
    alerts = nb.alert_table(y, base, score, threshold=4.0)
    out = nb.alert_episodes(alerts)
    assert list(out.columns) == ["start", "end", "days", "worst_score"]
    assert list(out.index) == [0, 1, 2]
    assert out["start"].tolist() == list(pd.to_datetime(["2024-03-02", "2024-03-05", "2024-03-07"]))
    assert out["end"].tolist() == list(pd.to_datetime(["2024-03-03", "2024-03-05", "2024-03-07"]))
    assert out["days"].tolist() == [2, 1, 1]
    assert out["worst_score"].tolist() == pytest.approx([-9.0, 4.5, -4.2])
    empty = nb.alert_episodes(alerts.iloc[:0])
    assert empty.empty and list(empty.columns) == ["start", "end", "days", "worst_score"]


def test_triage(nb):
    y, base, score = alert_inputs()
    alerts = nb.alert_table(y, base, score, threshold=4.0)
    day = pd.DataFrame({"holiday": [0, 1, 0, 0, 0, 0, 0, 0], "weathersit": [1, 3, 3, 1, 1, 1, 2, 1]},
                       index=y.index)
    before = alerts.copy()
    out = nb.triage(alerts, day)
    pd.testing.assert_frame_equal(alerts, before)
    assert out["reason"].tolist() == ["holiday", "bad_weather", "investigate", "investigate"]


def test_triage_partial_day(nb):
    y, base, score = alert_inputs()
    alerts = nb.alert_table(y, base, score, threshold=4.0)
    day = pd.DataFrame({"holiday": [0, 1, 0, 0, 0, 0, 0, 0], "weathersit": [1, 3, 3, 1, 1, 1, 2, 1]},
                       index=y.index)
    # 02/03 chỉ 5 giờ (thiếu giờ thắng cả holiday); 05/03 đủ 24; 07/03 không có trong coverage (0 giờ)
    coverage = pd.Series([24, 5, 24, 24, 24, 24], index=y.index[:6], name="hours")
    out = nb.triage(alerts, day, coverage)
    assert out["reason"].tolist() == ["partial_day", "bad_weather", "investigate", "partial_day"]
    out = nb.triage(alerts, day, coverage, min_hours=4)
    assert out["reason"].tolist() == ["holiday", "bad_weather", "investigate", "partial_day"]


def test_hour_coverage(nb):
    hour = pd.DataFrame({"dteday": pd.to_datetime(["2024-01-02", "2024-01-01", "2024-01-01", "2024-01-01"]),
                         "hr": [5, 0, 1, 1]})
    before = hour.copy()
    out = nb.hour_coverage(hour)
    pd.testing.assert_frame_equal(hour, before)
    assert out.name == "hours" and out.index.name == "date"
    assert list(out.index) == list(pd.to_datetime(["2024-01-01", "2024-01-02"]))
    assert out.tolist() == [2, 1]


@pytest.fixture(scope="module")
def real():
    root = ex.dataset("bike-sharing-uci")
    day = pd.read_csv(root / "day.csv", parse_dates=["dteday"]).set_index("dteday")
    hour = pd.read_csv(root / "hour.csv", parse_dates=["dteday"])
    return day, day["cnt"].astype(float), hour


def test_real_alerts(nb, real):
    day, y, hour = real
    base = nb.seasonal_baseline(y)
    score = nb.robust_score(y, base)
    assert score.notna().sum() == 675
    assert score.first_valid_index() == pd.Timestamp("2011-02-26")
    alerts = nb.alert_table(y, base, score)
    assert len(alerts) == 39
    assert (alerts["direction"] == "drop").sum() == 36
    # score âm nhất (−57.9, 29/10/2012) là artifact: ngày đó hour.csv chỉ có 1 giờ (22 lượt), không đo cầu
    worst = alerts["score"].idxmin()
    assert worst == pd.Timestamp("2012-10-29")
    assert alerts.loc[worst, "baseline"] == pytest.approx(6326.5)
    assert alerts.loc[worst, "score"] == pytest.approx(-57.94, abs=0.01)
    assert len(nb.alert_episodes(alerts)) == 26
    coverage = nb.hour_coverage(hour)
    assert len(coverage) == 731 and (coverage < 24).sum() == 76
    assert coverage.loc["2012-10-29"] == 1 and coverage.loc["2012-10-30"] == 11
    assert nb.triage(alerts, day)["reason"].value_counts().to_dict() == {"investigate": 25, "bad_weather": 11,
                                                                         "holiday": 3}
    triaged = nb.triage(alerts, day, coverage)
    assert triaged["reason"].value_counts().to_dict() == {"investigate": 23, "bad_weather": 10, "partial_day": 3,
                                                          "holiday": 3}
    assert sorted(triaged.index[triaged["reason"] == "partial_day"].strftime("%Y-%m-%d")) == [
        "2011-08-27", "2012-10-29", "2012-10-30"]
    real_days = triaged[triaged["reason"] != "partial_day"]
    assert real_days["score"].idxmin() == pd.Timestamp("2012-12-26")     # cảnh báo lớn nhất trên ngày đủ giờ
