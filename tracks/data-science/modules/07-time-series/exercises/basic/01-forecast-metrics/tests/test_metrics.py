import numpy as np
import pytest
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error

from testkit import Exercise

ex = Exercise(__file__)

Y = np.array([120.0, 95.0, 130.0, 80.0, 150.0])
P = np.array([110.0, 100.0, 140.0, 60.0, 155.0])


@pytest.fixture(scope="module")
def mt():
    return ex.module("metrics.py")


def test_mae_rmse_match_sklearn(mt):
    assert mt.mae(Y, P) == pytest.approx(mean_absolute_error(Y, P))
    assert mt.rmse(Y, P) == pytest.approx(np.sqrt(mean_squared_error(Y, P)))


def test_accepts_lists_and_series(mt):
    import pandas as pd
    assert mt.mae(list(Y), pd.Series(P)) == pytest.approx(mean_absolute_error(Y, P))


def test_mape_matches_sklearn_as_fraction(mt):
    assert mt.mape(Y, P) == pytest.approx(mean_absolute_percentage_error(Y, P))


def test_mape_rejects_zero_actuals(mt):
    with pytest.raises(ValueError):
        mt.mape(np.array([10.0, 0.0, 5.0]), np.array([9.0, 1.0, 5.0]))


def test_mape_is_asymmetric(mt):
    # cùng sai số tuyệt đối 50: dự báo thấp bị phạt tối đa 100%, dự báo cao không có trần
    assert mt.mape([100.0], [50.0]) == pytest.approx(0.5)
    assert mt.mape([50.0], [100.0]) == pytest.approx(1.0)


def test_smape_formula_and_bounds(mt):
    expected = np.mean(2 * np.abs(Y - P) / (np.abs(Y) + np.abs(P)))
    assert mt.smape(Y, P) == pytest.approx(expected)
    assert mt.smape([0.0, 10.0], [0.0, 10.0]) == pytest.approx(0.0)   # 0/0 tính là 0
    assert mt.smape([0.0], [5.0]) == pytest.approx(2.0)               # trần là 2


def test_mase_hand_computed(mt):
    train = np.array([10.0, 12.0, 14.0, 13.0, 15.0])
    # scale = mean(|2|, |2|, |1|, |2|) = 1.75 ; MAE = mean(1, 3) = 2
    assert mt.mase([16.0, 14.0], [15.0, 17.0], train) == pytest.approx(2 / 1.75)


def test_mase_seasonal_scale(mt):
    rng = np.random.default_rng(0)
    week = np.array([30.0, 28, 27, 25, 22, 10, 12])
    train = np.tile(week, 8) + rng.normal(0, 2, 56)
    scale = np.mean(np.abs(train[7:] - train[:-7]))
    y, p = train[-7:] + 1, train[-7:]
    assert mt.mase(y, p, train, m=7) == pytest.approx(1.0 / scale)


def test_in_sample_seasonal_naive_has_mase_one(mt):
    rng = np.random.default_rng(1)
    train = rng.normal(100, 10, 200)
    assert mt.mase(train[7:], train[:-7], train, m=7) == pytest.approx(1.0)


def test_mase_is_scale_free(mt):
    train = np.array([10.0, 12.0, 14.0, 13.0, 15.0])
    a = mt.mase([16.0, 14.0], [15.0, 17.0], train)
    b = mt.mase([1600.0, 1400.0], [1500.0, 1700.0], train * 100)
    assert a == pytest.approx(b)


def test_mase_rejects_constant_train(mt):
    with pytest.raises(ValueError):
        mt.mase([5.0], [4.0], np.full(10, 5.0))
