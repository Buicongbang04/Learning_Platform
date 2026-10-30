import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
SUMMARY_COLUMNS = ["rides", "casual", "registered", "days", "per_day", "clear_days", "bad_days"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("diagnosis.ipynb")


def tiny_day():
    # 3 ngày tháng 1, 2 ngày tháng 2 (một ngày mưa to weathersit 4), thứ tự dòng bị xáo
    return pd.DataFrame({
        "dteday": ["2012-02-02", "2012-01-01", "2012-01-02", "2012-02-01", "2012-01-03"],
        "weathersit": [4, 1, 2, 1, 1],
        "casual": [10, 50, 20, 60, 40],
        "registered": [90, 150, 80, 240, 160],
        "cnt": [100, 200, 100, 300, 200],
    })


def test_month_summary(nb):
    day = tiny_day()
    before = day.copy()
    out = nb.month_summary(day)
    pd.testing.assert_frame_equal(day, before)
    assert list(out.columns) == SUMMARY_COLUMNS
    assert list(out.index) == list(pd.to_datetime(["2012-01-01", "2012-02-01"]))
    assert out.index.name == "month"
    jan, feb = out.iloc[0], out.iloc[1]
    assert jan[["rides", "casual", "registered", "days", "clear_days", "bad_days"]].tolist() == [500, 110, 390, 3, 2, 0]
    assert feb[["rides", "casual", "registered", "days", "clear_days", "bad_days"]].tolist() == [400, 70, 330, 2, 1, 1]
    assert out["per_day"].tolist() == pytest.approx([500 / 3, 200.0])


def test_segment_contribution(nb):
    out = nb.segment_contribution(tiny_day(), "2012-01-01", "2012-02-01")
    assert list(out.index) == ["casual", "registered"]
    assert list(out.columns) == ["before", "after", "change", "pct", "share_of_change"]
    assert out["before"].tolist() == [110, 390] and out["after"].tolist() == [70, 330]
    assert out["change"].tolist() == [-40, -60]
    assert out["pct"].tolist() == pytest.approx([70 / 110 - 1, 330 / 390 - 1])
    assert out["share_of_change"].tolist() == pytest.approx([0.4, 0.6])


def test_same_weather_change_only_shared_weather(nb):
    day = tiny_day()
    before = day.copy()
    out = nb.same_weather_change(day, "2012-01-01", "2012-02-01")
    pd.testing.assert_frame_equal(day, before)
    assert out.name == "change"
    # quang: TB tháng 1 = 200, tháng 2 = 300; mây chỉ có tháng 1, mưa to chỉ có tháng 2: bỏ
    assert list(out.index) == [1]
    assert out.tolist() == pytest.approx([0.5])


@pytest.fixture(scope="module")
def real_day():
    return pd.read_csv(ex.dataset("bike-sharing-uci") / "day.csv")


def test_real_month_summary(nb, real_day):
    out = nb.month_summary(real_day)
    assert len(out) == 24
    sep, oct_ = out.loc[pd.Timestamp("2012-09-01")], out.loc[pd.Timestamp("2012-10-01")]
    assert sep["rides"] == 218_573 and oct_["rides"] == 198_841
    assert oct_["per_day"] / sep["per_day"] - 1 == pytest.approx(-0.1196, abs=1e-4)
    assert (sep["clear_days"], oct_["clear_days"]) == (22, 14)
    assert (sep["bad_days"], oct_["bad_days"]) == (0, 2)
    prev = out.loc[pd.Timestamp("2011-10-01"), "per_day"] / out.loc[pd.Timestamp("2011-09-01"), "per_day"] - 1
    assert prev == pytest.approx(-0.0619, abs=1e-4)


def test_real_segments(nb, real_day):
    out = nb.segment_contribution(real_day, "2012-09-01", "2012-10-01")
    assert out["change"].tolist() == [-9240, -10492]
    assert out.loc["casual", "pct"] == pytest.approx(-0.2111, abs=1e-4)
    assert out.loc["casual", "share_of_change"] == pytest.approx(0.4683, abs=1e-4)


def test_real_same_weather(nb, real_day):
    out = nb.same_weather_change(real_day, "2012-09-01", "2012-10-01")
    assert list(out.index) == [1, 2]
    assert out.tolist() == pytest.approx([-0.0262, -0.0415], abs=1e-4)
