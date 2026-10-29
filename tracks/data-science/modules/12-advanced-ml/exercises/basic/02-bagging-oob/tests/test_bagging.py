import numpy as np
import pytest
from sklearn.tree import DecisionTreeRegressor

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def bag():
    return ex.module("bagging.py")


def make_data(n: int, seed: int):
    rng = np.random.default_rng(seed)
    X = rng.uniform(-2, 2, size=(n, 4))
    y = np.sin(2 * X[:, 0]) + X[:, 1] * X[:, 2] + rng.normal(0, 0.5, n)
    return X, y


def mse(a, b):
    return float(np.mean((np.asarray(a) - np.asarray(b)) ** 2))


def test_expected_oob_fraction(bag):
    assert bag.expected_oob_fraction(1) == pytest.approx(0.0)
    assert bag.expected_oob_fraction(2) == pytest.approx(0.25)
    assert bag.expected_oob_fraction(10) == pytest.approx(0.9 ** 10)
    assert bag.expected_oob_fraction(100_000) == pytest.approx(np.exp(-1), abs=1e-5)


def test_shapes_and_reproducibility(bag):
    X, y = make_data(300, 0)
    X_test, _ = make_data(50, 1)
    a = bag.bagging_fit_predict(X, y, X_test, n_estimators=20, seed=3)
    b = bag.bagging_fit_predict(X, y, X_test, n_estimators=20, seed=3)
    c = bag.bagging_fit_predict(X, y, X_test, n_estimators=20, seed=4)
    assert a[0].shape == (50,) and a[1].shape == (300,)
    assert np.allclose(a[0], b[0]) and np.allclose(a[1], b[1], equal_nan=True)
    assert not np.allclose(a[0], c[0])


def test_single_tree_leaves_about_a_third_out_of_bag(bag):
    X, y = make_data(2000, 2)
    _, oob = bag.bagging_fit_predict(X, y, X[:5], n_estimators=1, seed=0)
    assert np.isnan(oob).mean() == pytest.approx(1 - np.exp(-1), abs=0.04)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_bagging_reduces_variance_of_deep_trees(bag, seed):
    X, y = make_data(600, seed)
    X_test, y_test = make_data(2000, seed + 50)
    single = DecisionTreeRegressor(random_state=0).fit(X, y).predict(X_test)
    bagged, _ = bag.bagging_fit_predict(X, y, X_test, n_estimators=100, seed=seed)
    assert mse(bagged, y_test) < 0.75 * mse(single, y_test)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_oob_error_estimates_test_error(bag, seed):
    X, y = make_data(600, seed)
    X_test, y_test = make_data(2000, seed + 50)
    pred, oob = bag.bagging_fit_predict(X, y, X_test, n_estimators=100, seed=seed)
    assert not np.isnan(oob).any()
    test_mse = mse(pred, y_test)
    oob_mse = mse(oob, y)
    # Nếu dùng nhầm cả cây đã thấy điểm i, OOB MSE sẽ thấp hơn hẳn (cây sâu thuộc lòng train)
    assert oob_mse == pytest.approx(test_mse, rel=0.25)


def test_feature_subsampling_is_used(bag):
    X, y = make_data(400, 5)
    X_test, _ = make_data(100, 6)
    full, _ = bag.bagging_fit_predict(X, y, X_test, n_estimators=30, seed=0)
    sub, _ = bag.bagging_fit_predict(X, y, X_test, n_estimators=30, seed=0, max_features=0.5)
    assert not np.allclose(full, sub)
