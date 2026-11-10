import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import HistGradientBoostingRegressor

from testkit import Exercise

ex = Exercise(__file__)
FEATURES = ["trip_distance", "hour", "dow", "PULocationID", "DOLocationID"]


def make_frame(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "trip_distance": np.round(rng.gamma(2.0, 1.5, n) + 0.3, 2),
            "hour": rng.integers(0, 24, n),
            "dow": rng.integers(0, 7, n),
            "PULocationID": rng.integers(1, 266, n),
            "DOLocationID": rng.integers(1, 266, n),
        }
    )


def durations(X: pd.DataFrame, seed: int, sign: float = 1.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rush = X["hour"].isin([16, 17, 18, 19]).to_numpy()
    return 4 + sign * 3.2 * X["trip_distance"].to_numpy() + 3.0 * rush + rng.normal(0, 1.5, len(X))


@pytest.fixture(scope="module")
def train_X():
    return make_frame(4000, 0)


@pytest.fixture(scope="module")
def X():
    return make_frame(600, 1)


@pytest.fixture(scope="module")
def good_predict(train_X):
    model = HistGradientBoostingRegressor(max_iter=80, random_state=0).fit(train_X[FEATURES], durations(train_X, 0))
    return lambda df: model.predict(df[FEATURES])


@pytest.fixture(scope="module")
def positional_predict(train_X):
    model = HistGradientBoostingRegressor(max_iter=80, random_state=0).fit(train_X[FEATURES].to_numpy(), durations(train_X, 0))
    return lambda df: model.predict(df.to_numpy())


@pytest.fixture(scope="module")
def inverted_predict(train_X):
    model = HistGradientBoostingRegressor(max_iter=80, random_state=0).fit(train_X[FEATURES], 40 + durations(train_X, 0, sign=-1.0))
    return lambda df: model.predict(df[FEATURES])


@pytest.fixture(scope="module")
def behavior():
    return ex.module("behavior.py")


def test_measures_are_zero_for_a_model_that_selects_columns_by_name(behavior, good_predict, X):
    assert behavior.column_order_shift(good_predict, X) == pytest.approx(0.0, abs=1e-9)
    mean_delta, violation_rate = behavior.distance_effect(good_predict, X)
    assert mean_delta > 0.5
    assert 0 <= violation_rate < 0.2


def test_measures_do_not_mutate_the_input(behavior, good_predict, X):
    before = X.copy()
    behavior.column_order_shift(good_predict, X)
    behavior.distance_effect(good_predict, X)
    pd.testing.assert_frame_equal(X, before)


def test_distance_effect_only_changes_the_requested_column(behavior, X):
    seen = []

    def spy(df):
        seen.append(df.copy())
        return np.zeros(len(df))

    behavior.distance_effect(spy, X, factor=2.0)
    original, scaled = sorted(seen[:2], key=lambda df: df["trip_distance"].sum())
    pd.testing.assert_series_equal(scaled["trip_distance"], original["trip_distance"] * 2.0)
    pd.testing.assert_frame_equal(scaled.drop(columns="trip_distance"), original.drop(columns="trip_distance"))


def test_good_model_passes_both_checks(behavior, good_predict, X):
    behavior.assert_column_order_invariant(good_predict, X)
    behavior.assert_distance_monotonic(good_predict, X)


def test_positional_model_is_caught_by_column_order_check(behavior, positional_predict, good_predict, X):
    assert behavior.column_order_shift(positional_predict, X) > 1.0
    with pytest.raises(AssertionError, match=r"\d"):
        behavior.assert_column_order_invariant(positional_predict, X)
    behavior.assert_distance_monotonic(positional_predict, X)


def test_inverted_model_is_caught_by_directional_check(behavior, inverted_predict, X):
    mean_delta, violation_rate = behavior.distance_effect(inverted_predict, X)
    assert mean_delta < 0 and violation_rate > 0.5
    with pytest.raises(AssertionError, match=r"\d"):
        behavior.assert_distance_monotonic(inverted_predict, X)
    behavior.assert_column_order_invariant(inverted_predict, X)


def test_violation_rate_limit_is_enforced_separately_from_the_mean(behavior, X):
    def mostly_up_sometimes_down(df):
        distance = df["trip_distance"].to_numpy()
        return np.where(np.arange(len(df)) % 3 == 0, -distance, 5 * distance)

    mean_delta, violation_rate = behavior.distance_effect(mostly_up_sometimes_down, X)
    assert mean_delta > 0 and violation_rate == pytest.approx(1 / 3, abs=0.01)
    with pytest.raises(AssertionError):
        behavior.assert_distance_monotonic(mostly_up_sometimes_down, X, max_violation_rate=0.2)
    behavior.assert_distance_monotonic(mostly_up_sometimes_down, X, max_violation_rate=0.4)
