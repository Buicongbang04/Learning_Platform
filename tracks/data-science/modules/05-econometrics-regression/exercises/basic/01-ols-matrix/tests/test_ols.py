import numpy as np
import pytest
import statsmodels.api as sm

from testkit import Exercise

ex = Exercise(__file__)

KEYS = {"beta", "resid", "sigma2", "se", "t", "p", "r2", "adj_r2"}


@pytest.fixture(scope="module")
def ols():
    return ex.module("ols.py")


def simulate(seed: int, n: int = 300):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3))
    X[:, 1] += 0.6 * X[:, 0]                      # hai biến tương quan
    y = 1.5 + X @ np.array([2.0, -1.0, 0.0]) + rng.normal(scale=2.0, size=n)
    return X, y


def test_add_intercept(ols):
    X = np.arange(6.0).reshape(3, 2)
    out = ols.add_intercept(X)
    assert out.shape == (3, 3)
    assert np.all(out[:, 0] == 1) and np.array_equal(out[:, 1:], X)
    assert ols.add_intercept(np.array([1.0, 2.0])).shape == (2, 2)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_matches_statsmodels(ols, seed):
    X, y = simulate(seed)
    Xc = ols.add_intercept(X)
    fit = ols.ols_fit(Xc, y)
    ref = sm.OLS(y, Xc).fit()
    assert KEYS <= set(fit)
    for key, value in [("beta", ref.params), ("se", ref.bse), ("t", ref.tvalues), ("p", ref.pvalues),
                       ("resid", ref.resid)]:
        assert np.asarray(fit[key]) == pytest.approx(np.asarray(value), abs=1e-8), key
    assert fit["sigma2"] == pytest.approx(ref.scale, rel=1e-10)
    assert fit["r2"] == pytest.approx(ref.rsquared, abs=1e-10)
    assert fit["adj_r2"] == pytest.approx(ref.rsquared_adj, abs=1e-10)


def test_residuals_orthogonal_to_X(ols):
    X, y = simulate(3)
    Xc = ols.add_intercept(X)
    resid = np.asarray(ols.ols_fit(Xc, y)["resid"])
    assert resid.sum() == pytest.approx(0, abs=1e-8)
    assert Xc.T @ resid == pytest.approx(np.zeros(Xc.shape[1]), abs=1e-7)


def test_grunfeld_pooled(ols):
    g = sm.datasets.grunfeld.load_pandas().data
    fit = ols.ols_fit(ols.add_intercept(g[["value", "capital"]].to_numpy()), g["invest"].to_numpy())
    assert np.asarray(fit["beta"])[1:] == pytest.approx([0.1145, 0.2275], abs=5e-5)
    assert fit["r2"] == pytest.approx(0.8179, abs=1e-4)


def test_rank_deficient_raises(ols):
    X, y = simulate(4)
    X = np.column_stack([X, X[:, 0] + X[:, 1]])  # cột cuối là tổng hai cột đầu
    with pytest.raises(ValueError):
        ols.ols_fit(ols.add_intercept(X), y)
