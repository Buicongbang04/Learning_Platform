import numpy as np
import pandas as pd
import pytest

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)


def correlated_pair(rho, n=6000, seed=0):
    rng = np.random.default_rng(seed)
    cov = [[1.0, rho], [rho, 1.0]]
    xy = rng.multivariate_normal([0, 0], cov, n)
    return pd.DataFrame({"x": xy[:, 0], "y": xy[:, 1], "noise": rng.normal(size=n)})


def test_correlation_flip_hides_from_marginals_but_not_from_classifier():
    mod = ex.module("multivariate.py")
    ref = correlated_pair(0.9, seed=1)
    cur = correlated_pair(-0.9, seed=2)
    features = ["x", "y", "noise"]
    assert mod.max_feature_psi(ref, cur, features) < 0.1
    assert mod.domain_auc(ref, cur, features) > 0.85


def test_same_distribution_has_auc_near_half():
    mod = ex.module("multivariate.py")
    auc = mod.domain_auc(correlated_pair(0.5, seed=3), correlated_pair(0.5, seed=4), ["x", "y", "noise"])
    assert 0.45 <= auc <= 0.55


def test_domain_auc_is_deterministic_and_respects_max_rows():
    mod = ex.module("multivariate.py")
    ref, cur = correlated_pair(0.9, seed=5), correlated_pair(-0.9, seed=6)
    features = ["x", "y"]
    a = mod.domain_auc(ref, cur, features, seed=0, max_rows=1000)
    b = mod.domain_auc(ref, cur, features, seed=0, max_rows=1000)
    assert a == b
    assert mod.domain_auc(ref, cur, features, seed=0, max_rows=1000) != mod.domain_auc(ref, cur, features, seed=0, max_rows=3000)


def test_missing_values_are_filled_with_minus_one():
    mod = ex.module("multivariate.py")
    rng = np.random.default_rng(7)
    ref = pd.DataFrame({"x": rng.normal(size=3000)})
    cur = pd.DataFrame({"x": rng.normal(size=3000)})
    cur.loc[cur.sample(frac=0.3, random_state=0).index, "x"] = np.nan
    assert mod.domain_auc(ref, cur, ["x"]) > 0.6


def test_driver_features_rank_the_changed_columns_first():
    mod = ex.module("multivariate.py")
    ref = correlated_pair(0.9, seed=8)
    cur = correlated_pair(-0.9, seed=9)
    ranked = mod.driver_features(ref, cur, ["x", "y", "noise"])
    assert [f for f, _ in ranked][-1] == "noise"
    assert [i for _, i in ranked] == sorted([i for _, i in ranked], reverse=True)
    assert sum(i for _, i in ranked) == pytest.approx(1.0)


def test_verdict_marks_hidden_drift():
    mod = ex.module("multivariate.py")
    hidden = mod.multivariate_verdict(correlated_pair(0.9, seed=10), correlated_pair(-0.9, seed=11), ["x", "y", "noise"])
    assert hidden["hidden_drift"] is True
    assert hidden["max_psi"] < 0.1 and hidden["auc"] >= 0.7
    clean = mod.multivariate_verdict(correlated_pair(0.5, seed=12), correlated_pair(0.5, seed=13), ["x", "y", "noise"])
    assert clean["hidden_drift"] is False


def real_frame(dataset, month):
    df = pd.read_parquet(
        mlopskit.real_month(dataset, month),
        columns=["trip_distance", "tpep_pickup_datetime", "PULocationID", "passenger_count"],
    ).sample(n=20_000, random_state=0)
    df["hour"] = df["tpep_pickup_datetime"].dt.hour
    return df


def test_real_months_season_vs_covid():
    mod = ex.module("multivariate.py")
    features = ["trip_distance", "hour", "PULocationID", "passenger_count"]
    jul, dec = real_frame("nyc-tlc", "2019-07"), real_frame("nyc-tlc", "2019-12")
    feb, apr = real_frame("nyc-tlc-2020", "2020-02"), real_frame("nyc-tlc-2020", "2020-04")
    seasonal = mod.domain_auc(jul, dec, features)
    covid = mod.domain_auc(feb, apr, features)
    assert seasonal < 0.6
    assert 0.65 <= covid <= 0.85
    assert covid > seasonal + 0.1
