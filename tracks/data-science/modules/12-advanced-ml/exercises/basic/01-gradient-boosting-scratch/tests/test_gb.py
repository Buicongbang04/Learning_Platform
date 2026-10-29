import numpy as np
import pytest
from sklearn.ensemble import GradientBoostingRegressor

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def gb():
    return ex.module("gb.py")


def make_data(n: int = 400, seed: int = 0, outliers: float = 0.0):
    rng = np.random.default_rng(seed)
    X = rng.uniform(-3, 3, size=(n, 3))
    y = np.sin(X[:, 0]) + 0.3 * X[:, 1] ** 2 + rng.normal(0, 0.3, n)
    if outliers:
        bad = rng.random(n) < outliers
        y = y + bad * rng.choice([-1, 1], n) * rng.uniform(20, 40, n)
    return X, y


def test_zero_trees_is_the_best_constant(gb):
    X, y = make_data()
    sq = gb.fit_gb(X, y, n_estimators=5, loss="squared")
    ab = gb.fit_gb(X, y, n_estimators=5, loss="absolute")
    assert np.allclose(gb.predict_gb(sq, X, n_trees=0), y.mean())
    assert np.allclose(gb.predict_gb(ab, X, n_trees=0), np.median(y))


def test_squared_loss_matches_sklearn(gb):
    X, y = make_data(seed=1)
    model = gb.fit_gb(X, y, n_estimators=60, learning_rate=0.1, max_depth=3)
    ref = GradientBoostingRegressor(n_estimators=60, learning_rate=0.1, max_depth=3, random_state=0).fit(X, y)
    assert np.abs(gb.predict_gb(model, X) - ref.predict(X)).max() < 1e-8
    # điểm mới: sklearn đổi X sang float32 nên ngưỡng cắt có thể lệch cực nhỏ, chỉ hiếm điểm khác
    X_new, _ = make_data(n=200, seed=2)
    assert np.mean(np.abs(gb.predict_gb(model, X_new) - ref.predict(X_new))) < 1e-3


def test_partial_prediction_uses_first_trees(gb):
    X, y = make_data(seed=3)
    model = gb.fit_gb(X, y, n_estimators=30, learning_rate=0.2, max_depth=2)
    ref = GradientBoostingRegressor(n_estimators=30, learning_rate=0.2, max_depth=2, random_state=0).fit(X, y)
    staged = list(ref.staged_predict(X))
    assert np.allclose(gb.predict_gb(model, X, n_trees=10), staged[9])
    assert np.allclose(gb.predict_gb(model, X), staged[-1])


def test_training_loss_never_increases_for_squared(gb):
    X, y = make_data(seed=4)
    model = gb.fit_gb(X, y, n_estimators=80, learning_rate=0.1, max_depth=2)
    losses = gb.staged_loss(model, X, y)
    assert len(losses) == 81
    assert losses[0] == pytest.approx(np.var(y))
    assert np.all(np.diff(losses) <= 1e-12)
    assert losses[-1] < 0.3 * losses[0]


def test_smaller_learning_rate_needs_more_trees(gb):
    X, y = make_data(seed=5)
    fast = gb.staged_loss(gb.fit_gb(X, y, n_estimators=50, learning_rate=0.5), X, y)
    slow = gb.staged_loss(gb.fit_gb(X, y, n_estimators=50, learning_rate=0.05), X, y)
    assert slow[10] > fast[10]


def test_absolute_leaf_values_are_medians(gb):
    X, y = make_data(seed=6, outliers=0.05)
    model = gb.fit_gb(X, y, n_estimators=1, learning_rate=1.0, max_depth=1, loss="absolute")
    pred = gb.predict_gb(model, X)
    groups = np.unique(pred)
    assert len(groups) == 2
    for value in groups:
        assert value == pytest.approx(np.median(y[pred == value]))


def test_absolute_loss_decreases_mae(gb):
    X, y = make_data(seed=7, outliers=0.05)
    model = gb.fit_gb(X, y, n_estimators=150, learning_rate=0.1, max_depth=3, loss="absolute")
    mae = gb.staged_loss(model, X, y)
    assert len(mae) == 151
    assert mae[0] == pytest.approx(np.mean(np.abs(y - np.median(y))))
    assert mae[-1] < 0.85 * mae[0]


@pytest.mark.parametrize("seed", [10, 11, 12])
def test_absolute_loss_is_robust_to_outliers(gb, seed):
    X, y = make_data(n=500, seed=seed, outliers=0.08)
    X_test, y_clean = make_data(n=500, seed=seed + 100)
    kw = dict(n_estimators=100, learning_rate=0.1, max_depth=3)
    sq = gb.predict_gb(gb.fit_gb(X, y, loss="squared", **kw), X_test)
    ab = gb.predict_gb(gb.fit_gb(X, y, loss="absolute", **kw), X_test)
    assert np.mean(np.abs(ab - y_clean)) < 0.7 * np.mean(np.abs(sq - y_clean))


def test_unknown_loss_raises(gb):
    X, y = make_data(n=50)
    with pytest.raises(ValueError):
        gb.fit_gb(X, y, loss="huber")
