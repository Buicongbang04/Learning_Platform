import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("morning_signal.ipynb")


def tiny_hour():
    # 3 ngày; ngày 2 (cuối tuần) không có giờ nào trước 10h; thứ tự dòng bị xáo
    return pd.DataFrame({
        "dteday": ["2011-01-03", "2011-01-03", "2011-01-03", "2011-01-01", "2011-01-01",
                   "2011-01-02", "2011-01-02", "2011-01-01"],
        "hr": [8, 9, 17, 7, 10, 12, 18, 9],
        "workingday": [1, 1, 1, 0, 0, 0, 0, 0],
        "cnt": [30, 20, 150, 4, 40, 50, 30, 6],
    })


def test_daily_signal_sums_morning_before_cutoff(nb):
    out = nb.daily_signal(tiny_hour())
    assert list(out.columns) == ["morning", "total", "workingday"]
    assert list(out.index) == list(pd.to_datetime(["2011-01-01", "2011-01-02", "2011-01-03"]))
    assert out.index.name == "dteday"
    # ngày 1: giờ 7 và 9 trước 10h (giờ 10 không tính); ngày 2: không có giờ nào trước 10h
    assert out["morning"].tolist() == [10, 0, 50]
    assert out["total"].tolist() == [50, 80, 200]
    assert out["workingday"].tolist() == [0, 0, 1]


def test_daily_signal_cutoff_and_no_mutation(nb):
    hour = tiny_hour()
    before = hour.copy()
    out = nb.daily_signal(hour, cutoff=9)
    pd.testing.assert_frame_equal(hour, before)
    assert out["morning"].tolist() == [4, 0, 30]


def test_morning_share_is_ratio_of_sums(nb):
    daily = pd.DataFrame({"morning": [10, 0, 50, 30], "total": [50, 80, 200, 100], "workingday": [0, 0, 1, 1]},
                         index=pd.to_datetime(["2011-01-01", "2011-01-02", "2011-01-03", "2011-01-04"]))
    out = nb.morning_share(daily)
    assert out.name == "share"
    assert list(out.index) == [0, 1]
    # tỉ lệ của tổng: 10 / 130 và 80 / 300 (trung bình tỉ lệ từng ngày sẽ ra 0.1 và 0.275)
    assert out.tolist() == pytest.approx([10 / 130, 80 / 300])


def test_nowcast_uses_share_of_day_type(nb):
    daily = pd.DataFrame({"morning": [10, 60], "total": [50, 200], "workingday": [0, 1]},
                         index=pd.to_datetime(["2011-01-01", "2011-01-03"]))
    out = nb.nowcast(daily, pd.Series({0: 0.2, 1: 0.25}))
    assert out.name == "forecast"
    assert list(out.index) == list(daily.index)
    assert out.tolist() == pytest.approx([50.0, 240.0])


def test_median_ape_skips_zero_actual(nb):
    actual = pd.Series([100.0, 200.0, 0.0, 50.0])
    forecast = pd.Series([110.0, 150.0, 10.0, 50.0])
    # sai số: 0.10, 0.25, (bỏ), 0.0 -> trung vị 0.10
    assert nb.median_ape(actual, forecast) == pytest.approx(0.10)


@pytest.fixture(scope="module")
def real_hour():
    return pd.read_csv(ex.dataset("bike-sharing-uci") / "hour.csv")


def daily_of(nb, real_hour):
    """Gọi trong thân test (không trong fixture) để starter FAIL chứ không ERROR."""
    return nb.daily_signal(real_hour)


def test_real_daily_signal(nb, real_hour):
    real_daily = daily_of(nb, real_hour)
    assert len(real_daily) == 731
    assert real_daily["total"].sum() == 3_292_679
    assert int((real_daily["morning"] == 0).sum()) == 3


def test_real_share_and_error(nb, real_hour):
    real_daily = daily_of(nb, real_hour)
    share = nb.morning_share(real_daily)
    assert share[0] == pytest.approx(0.1370, abs=1e-4)
    assert share[1] == pytest.approx(0.2614, abs=1e-4)
    seg = nb.nowcast(real_daily, share)
    assert nb.median_ape(real_daily["total"], seg) == pytest.approx(0.0886, abs=1e-4)
    pooled = real_daily["morning"].sum() / real_daily["total"].sum()
    one = nb.nowcast(real_daily, pd.Series({0: pooled, 1: pooled}))
    assert nb.median_ape(real_daily["total"], one) == pytest.approx(0.2504, abs=1e-4)


def test_real_out_of_sample(nb, real_hour):
    real_daily = daily_of(nb, real_hour)
    train = real_daily[real_daily.index.year == 2011]
    test = real_daily[real_daily.index.year == 2012]
    error = nb.median_ape(test["total"], nb.nowcast(test, nb.morning_share(train)))
    assert error == pytest.approx(0.0800, abs=1e-4)
