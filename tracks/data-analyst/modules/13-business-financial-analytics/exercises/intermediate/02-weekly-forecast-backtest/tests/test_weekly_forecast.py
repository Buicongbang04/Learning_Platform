import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("weekly_forecast.ipynb")


def tiny_train():
    # 14 ngày từ thứ Hai 06/01/2014 tới Chủ nhật 19/01/2014 + thứ Hai 20/01 (tuần dở dang).
    # Cửa hàng 1 đủ ngày; cửa hàng 2 thiếu ngày 10/01; cửa hàng 3 đủ ngày.
    days = pd.date_range("2014-01-06", "2014-01-20", freq="D")
    rows = []
    for store in (1, 2, 3):
        for i, d in enumerate(days):
            if store == 2 and d == pd.Timestamp("2014-01-10"):
                continue
            promo = int(d.dayofweek < 5 and d < pd.Timestamp("2014-01-13") and store != 3)
            rows.append({"Store": store, "Date": d, "Sales": 100 * store + i, "Promo": promo, "Open": 1})
    return pd.DataFrame(rows)


def test_comparable_stores(nb):
    tr = tiny_train()
    before = tr.copy()
    out = nb.comparable_stores(tr)
    pd.testing.assert_frame_equal(tr, before)
    assert isinstance(out, pd.Index)
    assert list(out) == [1, 3]
    assert out.name == "Store"


def test_weekly_sales(nb):
    tr = tiny_train()
    out = nb.weekly_sales(tr, pd.Index([1, 3]))
    assert list(out.columns) == ["sales", "promo"]
    assert out.index.name == "week"
    assert list(out.index) == list(pd.to_datetime(["2014-01-06", "2014-01-13"]))
    # tuần 1: cửa hàng 1 = 7*100 + (0+..+6), cửa hàng 3 = 7*300 + 21
    assert out["sales"].tolist() == [700 + 21 + 2100 + 21, 700 + 70 + 2100 + 70]
    assert out["promo"].tolist() == [1, 0]
    assert out["promo"].dtype.kind == "i"


def history(n=60, start="2020-01-06"):
    idx = pd.date_range(start, periods=n, freq="7D")
    return pd.Series(np.arange(n, dtype=float) + 100, index=idx, name="sales")


def test_seasonal_naive(nb):
    y = history(60)
    out = nb.seasonal_naive(y, 3, m=52)
    assert isinstance(out, np.ndarray)
    assert out.tolist() == [108.0, 109.0, 110.0]
    y4 = history(10)
    assert nb.seasonal_naive(y4, 6, m=4).tolist() == [106.0, 107.0, 108.0, 109.0, 106.0, 107.0]
    with pytest.raises(ValueError):
        nb.seasonal_naive(history(10), 2, m=52)


def test_moving_average(nb):
    out = nb.moving_average(history(10), 3, k=4)
    assert out.tolist() == pytest.approx([107.5] * 3)


def test_promo_average(nb):
    idx = pd.date_range("2020-01-06", periods=10, freq="7D")
    y = pd.Series([10.0, 50.0, 12.0, 54.0, 14.0, 58.0, 16.0, 60.0], index=idx[:8])
    promo = pd.Series([0, 1, 0, 1, 0, 1, 0, 1, 1, 0], index=idx)
    out = nb.promo_average(y, 2, promo, k=2)
    # tuần 9 có promo -> TB 58, 60; tuần 10 không -> TB 14, 16
    assert out.tolist() == pytest.approx([59.0, 15.0])
    with pytest.raises(ValueError):
        nb.promo_average(y, 3, promo, k=2)


def weekly_fixture():
    idx = pd.date_range("2020-01-06", periods=12, freq="7D")
    return pd.DataFrame({"sales": [100.0, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210],
                         "promo": [0, 1] * 6}, index=pd.Index(idx, name="week"))


def test_backtest_and_summarize(nb):
    weekly = weekly_fixture()
    before = weekly.copy()
    seen = []

    def last(hist, h, promo):
        seen.append((hist.index[-1], len(promo)))
        return np.repeat(hist.iloc[-1], h)

    forecasters = {"last": last, "ten": lambda hist, h, promo: np.full(h, 10.0)}
    out = nb.backtest(weekly, forecasters, ["2020-02-17", "2020-03-02"], h=2)
    pd.testing.assert_frame_equal(weekly, before)
    assert list(out.columns) == ["cutoff", "method", "mape", "bias"]
    assert out["method"].tolist() == ["last", "ten", "last", "ten"]
    assert list(out["cutoff"]) == list(pd.to_datetime(["2020-02-17", "2020-02-17", "2020-03-02", "2020-03-02"]))
    # cutoff 17/02 (vị trí 6): lịch sử tới 150, thực tế 160, 170
    assert out.loc[0, "mape"] == pytest.approx((10 / 160 + 20 / 170) / 2)
    assert out.loc[0, "bias"] == pytest.approx((150 * 2 - 330) / 330)
    assert seen[0] == (pd.Timestamp("2020-02-10"), 12)
    assert out.loc[3, "mape"] == pytest.approx((170 / 180 + 180 / 190) / 2)
    with pytest.raises(ValueError):
        nb.backtest(weekly, forecasters, ["2020-03-23"], h=2)
    summary = nb.summarize(out)
    assert list(summary.columns) == ["mape", "worst_mape", "bias"]
    assert list(summary.index) == ["last", "ten"]
    assert summary.loc["ten", "worst_mape"] == pytest.approx(out.loc[[1, 3], "mape"].max())


_W = {}


def real_weekly(nb):
    """Chuỗi tuần tính một lần; gọi trong thân test để starter FAIL chứ không ERROR."""
    if not _W:
        train = pd.read_csv(ex.dataset("store-sales") / "train.csv", parse_dates=["Date"],
                            dtype={"StateHoliday": str})
        _W["stores"] = nb.comparable_stores(train)
        _W["weekly"] = nb.weekly_sales(train, _W["stores"])
    return _W["stores"], _W["weekly"]


def test_real_weekly(nb):
    stores, weekly = real_weekly(nb)
    assert len(stores) == 934
    assert len(weekly) == 133
    assert weekly.index[0] == pd.Timestamp("2013-01-07") and weekly.index[-1] == pd.Timestamp("2015-07-20")
    assert weekly["sales"].sum() == 5_065_433_519
    assert weekly["promo"].sum() == 71


def test_real_backtest(nb):
    _, weekly = real_weekly(nb)
    forecasters = {
        "seasonal_naive": lambda hist, h, promo: nb.seasonal_naive(hist, h),
        "moving_average": lambda hist, h, promo: nb.moving_average(hist, h),
        "promo_average": lambda hist, h, promo: nb.promo_average(hist, h, promo),
    }
    cutoffs = ["2015-01-05", "2015-02-02", "2015-03-02", "2015-03-30", "2015-04-27", "2015-05-25"]
    summary = nb.summarize(nb.backtest(weekly, forecasters, cutoffs))
    assert summary.loc["promo_average", "mape"] == pytest.approx(0.0626, abs=5e-4)
    assert summary.loc["seasonal_naive", "mape"] == pytest.approx(0.0631, abs=5e-4)
    assert summary.loc["moving_average", "mape"] == pytest.approx(0.1482, abs=5e-4)
    # thứ hạng giữa promo_average và seasonal_naive là nhiễu (chênh khoảng 0.05 điểm): chỉ kiểm hai cái sát nhau
    # và moving_average đứng cuối
    assert summary.index[-1] == "moving_average"
    assert abs(summary.loc["promo_average", "mape"] - summary.loc["seasonal_naive", "mape"]) < 0.005
    assert summary.loc["seasonal_naive", "bias"] == pytest.approx(-0.0279, abs=1e-3)
