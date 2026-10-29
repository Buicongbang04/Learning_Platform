import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("bike_charts.ipynb")


def hours(rows):
    """rows: (dteday, season, weekday, hr, casual, registered); cnt = casual + registered."""
    df = pd.DataFrame(rows, columns=["dteday", "season", "weekday", "hr", "casual", "registered"])
    df["cnt"] = df.casual + df.registered
    df["mnth"] = pd.to_datetime(df.dteday).dt.month
    return df


SMALL = hours([
    # Thứ Hai 2011-01-03 (weekday 1), mùa 1
    ("2011-01-03", 1, 1, 8, 2, 18),
    ("2011-01-03", 1, 1, 17, 4, 26),
    # Thứ Hai tuần sau, cùng giờ: trung bình của hai ngày
    ("2011-01-10", 1, 1, 8, 6, 34),
    ("2011-01-10", 1, 1, 17, 0, 10),
    # Thứ Bảy 2011-07-02 (weekday 6), mùa 3
    ("2011-07-02", 3, 6, 13, 30, 20),
    # Thứ Tư 2011-04-06 (weekday 3), mùa 2
    ("2011-04-06", 2, 3, 8, 1, 59),
    ("2011-04-06", 2, 3, 9, 3, 7),
])


def test_daily_rides_sums_hours_per_day(nb):
    s = nb.daily_rides(SMALL)
    assert isinstance(s.index, pd.DatetimeIndex)
    assert list(s.index) == list(pd.to_datetime(["2011-01-03", "2011-01-10", "2011-04-06", "2011-07-02"]))
    assert s.tolist() == [50, 50, 70, 50]


def test_daily_rides_does_not_mutate_input(nb):
    before = SMALL.copy()
    nb.daily_rides(SMALL)
    pd.testing.assert_frame_equal(SMALL, before)


def test_rides_by_season_labels_and_sorted_desc(nb):
    s = nb.rides_by_season(SMALL)
    assert s.to_dict() == {"spring": 100, "summer": 70, "fall": 50}
    assert list(s.index) == ["spring", "summer", "fall"]          # giảm dần
    assert s.index[0] == "spring"


def test_rides_by_season_all_four_labels(nb):
    df = hours([("2011-01-01", k, 6, 0, 0, v) for k, v in [(1, 5), (2, 40), (3, 30), (4, 20)]])
    assert list(nb.rides_by_season(df).index) == ["summer", "fall", "winter", "spring"]


def test_weekday_hour_matrix_shape_and_values(nb):
    m = nb.weekday_hour_matrix(SMALL)
    assert m.shape == (7, 24)
    assert list(m.index) == list(range(7))
    assert list(m.columns) == list(range(24))
    assert m.loc[1, 8] == pytest.approx((20 + 40) / 2)            # trung bình hai thứ Hai lúc 8h
    assert m.loc[1, 17] == pytest.approx((30 + 10) / 2)
    assert m.loc[6, 13] == pytest.approx(50)
    assert m.loc[3, 9] == pytest.approx(10)
    assert np.isnan(m.loc[0, 8])                                   # không có dữ liệu: NaN, không phải 0
    assert m.notna().sum().sum() == 5


def test_casual_share_by_month(nb):
    out = nb.casual_share_by_month(SMALL)
    assert list(out.columns) == ["casual", "registered"]
    assert isinstance(out.index, pd.DatetimeIndex)
    assert list(out.index) == list(pd.to_datetime(["2011-01-01", "2011-04-01", "2011-07-01"]))
    assert out.loc["2011-01-01", "casual"] == pytest.approx(12 / 100)
    assert out.loc["2011-04-01", "registered"] == pytest.approx(66 / 70)
    assert out.loc["2011-07-01", "casual"] == pytest.approx(30 / 50)
    assert np.allclose(out.sum(axis=1), 1.0)


@pytest.fixture(scope="module")
def real_hour():
    return pd.read_csv(ex.dataset("bike-sharing-uci") / "hour.csv")


def test_real_daily_rides(nb, real_hour):
    s = nb.daily_rides(real_hour)
    assert len(s) == 731
    assert s.sum() == 3_292_679
    assert s[s.index.year == 2011].sum() == 1_243_103
    assert s[s.index.year == 2012].sum() == 2_049_576
    assert s.min() == 22                                            # 29/10/2012, bão Sandy


def test_real_rides_by_season(nb, real_hour):
    s = nb.rides_by_season(real_hour)
    assert set(s.index) == {"spring", "summer", "fall", "winter"}
    assert s.is_monotonic_decreasing
    assert s["spring"] == 471_348


def test_real_weekday_hour_matrix(nb, real_hour):
    m = nb.weekday_hour_matrix(real_hour)
    assert m.shape == (7, 24) and m.notna().all().all()
    assert m.stack().idxmax() == (2, 17)                            # thứ Ba 17h
    assert m.loc[2, 17] == pytest.approx(544, abs=1)


def test_real_casual_share_by_month(nb, real_hour):
    out = nb.casual_share_by_month(real_hour)
    assert out.shape == (24, 2)
    assert out.loc["2011-01-01", "casual"] == pytest.approx(0.0805, abs=5e-4)
    assert np.allclose(out.sum(axis=1), 1.0)
