import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def bt():
    return ex.module("backtest.py")


def naive(train, h):
    return np.full(h, train[-1])


def snaive7(train, h):
    return train[-7:][np.arange(h) % 7]


def weekly_series(seed, n=200):
    rng = np.random.default_rng(seed)
    return np.tile([30.0, 28, 27, 25, 22, 10, 12], n // 7 + 1)[:n] + 0.05 * np.arange(n) + rng.normal(0, 1.5, n)


def test_expanding_splits(bt):
    splits = bt.rolling_origin_splits(n=20, initial=10, horizon=3, step=2)
    assert [s[1][0] for s in splits] == [10, 12, 14, 16]          # 16 + 3 = 19 ≤ 20; 18 + 3 > 20
    for train, test in splits:
        np.testing.assert_array_equal(train, np.arange(0, test[0]))
        np.testing.assert_array_equal(test, np.arange(test[0], test[0] + 3))


def test_last_split_may_end_exactly_at_n(bt):
    splits = bt.rolling_origin_splits(n=13, initial=10, horizon=3, step=1)
    assert splits[-1][1][-1] == 12 and len(splits) == 1


def test_sliding_window_splits(bt):
    splits = bt.rolling_origin_splits(n=30, initial=12, horizon=5, step=5, window=8)
    assert len(splits) == 3
    for train, test in splits:
        assert len(train) == 8
        assert train[-1] == test[0] - 1


def test_invalid_arguments(bt):
    with pytest.raises(ValueError):
        bt.rolling_origin_splits(n=10, initial=9, horizon=3)
    with pytest.raises(ValueError):
        bt.rolling_origin_splits(n=30, initial=5, horizon=3, window=8)   # cửa sổ dài hơn dữ liệu train đầu tiên


def test_backtest_never_shows_the_future(bt):
    y = np.arange(100.0)
    seen = []

    def spy(train, h):
        seen.append((len(train), train[-1]))
        train[-1] = -999.0           # forecaster "nghịch dại" sửa dữ liệu: không được làm hỏng y
        return np.zeros(h)

    res = bt.backtest(y, spy, initial=60, horizon=7, step=10)
    assert seen == [(60, 59.0), (70, 69.0), (80, 79.0), (90, 89.0)]
    assert y[59] == 59.0
    assert list(res.columns) == ["cutoff", "h", "y_true", "y_pred"]
    assert len(res) == 4 * 7


def test_backtest_rows(bt):
    y = np.arange(30.0)
    res = bt.backtest(y, naive, initial=20, horizon=3, step=5)
    assert list(res.cutoff.unique()) == [20, 25]
    first = res[res.cutoff == 20]
    assert list(first.h) == [1, 2, 3]
    assert list(first.y_true) == [20.0, 21.0, 22.0]
    assert list(first.y_pred) == [19.0, 19.0, 19.0]


def test_backtest_accepts_series(bt):
    s = pd.Series(np.arange(30.0), index=pd.date_range("2018-01-01", periods=30))
    res = bt.backtest(s, naive, initial=20, horizon=3, step=5)
    assert list(res.y_pred[:3]) == [19.0, 19.0, 19.0]


def test_error_grows_with_horizon_for_random_walk(bt):
    rng = np.random.default_rng(0)
    y = np.cumsum(rng.normal(0, 1, 3000))
    res = bt.backtest(y, naive, initial=500, horizon=10, step=5)
    err = bt.error_by_horizon(res)
    assert list(err.index) == list(range(1, 11))
    # với random walk, MAE ở bước h tỉ lệ với sqrt(h)
    assert err.loc[10] / err.loc[1] == pytest.approx(np.sqrt(10), rel=0.25)


def test_compare_ranks_models(bt):
    y = weekly_series(1)
    table = bt.compare(y, {"naive": naive, "snaive": snaive7}, initial=100, horizon=14, step=7, m=7)
    assert list(table.columns) == ["mae", "mase"]
    assert table.index[0] == "snaive"
    assert table.loc["snaive", "mase"] < table.loc["naive", "mase"] / 2


def test_compare_mase_uses_each_training_window(bt):
    y = np.array([0.0, 2, 0, 2, 0, 2, 0, 2, 100, 100])
    # origin 1: train y[:6] (scale lag-1 = 2), test y[6:8] → naive 2 → MAE 1 → MASE 0.5
    # origin 2: train y[:8] (scale 2),          test y[8:10] → naive 2 → MAE 98 → MASE 49
    table = bt.compare(y, {"naive": naive}, initial=6, horizon=2, step=2, m=1)
    assert table.loc["naive", "mase"] == pytest.approx((0.5 + 49) / 2)
    assert table.loc["naive", "mae"] == pytest.approx((1 + 98) / 2)
