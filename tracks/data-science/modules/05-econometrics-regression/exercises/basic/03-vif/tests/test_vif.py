import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def vf():
    return ex.module("vif.py")


def make(seed: int, n: int = 500) -> pd.DataFrame:
    """Giống sản phẩm Olist: cân nặng và thể tích tương quan mạnh, giá tương quan vừa, khoảng cách độc lập."""
    rng = np.random.default_rng(seed)
    log_weight = rng.normal(6.5, 1.2, n)
    log_volume = 0.9 * log_weight + rng.normal(2.5, 0.5, n)
    log_price = 0.4 * log_weight + rng.normal(2, 0.8, n)
    log_distance = rng.normal(6, 1, n)
    return pd.DataFrame({"log_weight": log_weight, "log_volume": log_volume,
                         "log_price": log_price, "log_distance": log_distance})


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_matches_statsmodels_with_constant(vf, seed):
    df = make(seed)
    out = vf.vif(df)
    X = sm.add_constant(df).to_numpy()
    ref = [variance_inflation_factor(X, i) for i in range(1, X.shape[1])]
    assert list(out.index) == list(df.columns)
    assert out.to_numpy() == pytest.approx(ref, abs=1e-8)


def test_scale_invariant(vf):
    df = make(3)
    scaled = df.assign(log_weight=df.log_weight * 1000 + 50)
    assert vf.vif(scaled).to_numpy() == pytest.approx(vf.vif(df).to_numpy(), rel=1e-8)


def test_independent_columns_near_one(vf):
    rng = np.random.default_rng(4)
    df = pd.DataFrame(rng.normal(size=(5000, 3)), columns=["a", "b", "c"])
    assert vf.vif(df).to_numpy() == pytest.approx([1, 1, 1], abs=0.01)


def test_perfect_collinearity_is_inf(vf):
    rng = np.random.default_rng(5)
    df = pd.DataFrame({"log_length": rng.normal(3, 0.5, 300), "log_height": rng.normal(2.5, 0.6, 300),
                       "log_width": rng.normal(3, 0.4, 300), "other": rng.normal(size=300)})
    df["log_volume"] = df.log_length + df.log_height + df.log_width
    out = vf.vif(df)
    assert np.isinf(out[["log_length", "log_height", "log_width", "log_volume"]]).all()
    assert out["other"] == pytest.approx(1, abs=0.1)


def test_constant_column_raises(vf):
    df = make(6).assign(const=1.0)
    with pytest.raises(ValueError):
        vf.vif(df)


def test_prune_drops_one_of_duplicates(vf):
    df = make(7)
    rng = np.random.default_rng(7)
    df["weight_kg"] = np.exp(df.log_weight) / 1000
    df["log_weight_copy"] = df.log_weight + rng.normal(0, 0.01, len(df))   # gần trùng
    kept = vf.prune_by_vif(df, threshold=10)
    assert ("log_weight" in kept) != ("log_weight_copy" in kept)
    assert {"log_distance", "log_price", "log_volume"} <= set(kept)
    assert kept == [c for c in df.columns if c in kept]                     # thứ tự ban đầu
    assert vf.vif(df[kept]).max() <= 10


def test_prune_keeps_all_when_below_threshold(vf):
    df = make(8)
    assert vf.prune_by_vif(df, threshold=10) == list(df.columns)
    assert len(vf.prune_by_vif(df, threshold=1.0)) == 1
