import numpy as np
import pytest
from scipy import stats

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def mle():
    return ex.module("mle.py")


def test_bernoulli_mle_is_sample_rate(mle):
    x = np.array([0, 1, 0, 0, 1, 0, 0, 0, 0, 0])
    assert mle.bernoulli_mle(x) == pytest.approx(0.2)


def test_poisson_mle(mle):
    x = np.random.default_rng(0).poisson(9.4, 5000)
    assert mle.poisson_mle(x) == pytest.approx(x.mean())


def test_exponential_mle_returns_rate_not_scale(mle):
    x = np.random.default_rng(1).exponential(scale=12.5, size=5000)
    _, scale = stats.expon.fit(x, floc=0)
    assert mle.exponential_mle(x) == pytest.approx(1 / scale, rel=1e-9)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_lognormal_mle_matches_scipy(mle, seed):
    x = np.random.default_rng(seed).lognormal(4.69, 0.81, 3000)
    mu, sigma = mle.lognormal_mle(x)
    s, _, scale = stats.lognorm.fit(x, floc=0)
    assert mu == pytest.approx(np.log(scale), abs=1e-6)
    assert sigma == pytest.approx(s, abs=1e-6)


def test_lognormal_mle_uses_ddof_zero(mle):
    x = np.exp(np.array([1.0, 2.0, 3.0, 4.0]))
    mu, sigma = mle.lognormal_mle(x)
    assert mu == pytest.approx(2.5)
    assert sigma == pytest.approx(np.std([1.0, 2.0, 3.0, 4.0], ddof=0))


def test_lognormal_nll_matches_logpdf(mle):
    x = np.random.default_rng(3).lognormal(1.0, 0.5, 200)
    expected = -stats.lognorm.logpdf(x, s=0.7, scale=np.exp(1.2)).sum()
    assert mle.lognormal_nll(1.2, 0.7, x) == pytest.approx(expected, rel=1e-9)


def test_closed_form_minimises_nll(mle):
    x = np.random.default_rng(4).lognormal(2.0, 1.1, 1000)
    mu, sigma = mle.lognormal_mle(x)
    best = mle.lognormal_nll(mu, sigma, x)
    for dmu, dsig in [(0.05, 0), (-0.05, 0), (0, 0.05), (0, -0.05)]:
        assert mle.lognormal_nll(mu + dmu, sigma + dsig, x) > best


@pytest.mark.parametrize("seed", [5, 6])
def test_numeric_fit_agrees_with_closed_form(mle, seed):
    x = np.random.default_rng(seed).lognormal(4.69, 0.81, 2000)
    mu, sigma = mle.lognormal_mle(x)
    mu_num, sigma_num = mle.fit_lognormal_numeric(x)
    assert mu_num == pytest.approx(mu, abs=1e-3)
    assert sigma_num == pytest.approx(sigma, abs=1e-3)
