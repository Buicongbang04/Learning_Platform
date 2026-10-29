import numpy as np
import pytest
from scipy import stats

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def dist():
    return ex.module("distributions.py")


@pytest.mark.parametrize("k, n, p", [(0, 10, 0.3), (3, 10, 0.3), (10, 10, 0.3), (8, 100, 0.081), (40, 400, 0.128)])
def test_binom_pmf_matches_scipy(dist, k, n, p):
    assert dist.binom_pmf(k, n, p) == pytest.approx(stats.binom.pmf(k, n, p), rel=1e-9, abs=1e-15)


def test_binom_pmf_sums_to_one(dist):
    assert sum(dist.binom_pmf(k, 30, 0.2) for k in range(31)) == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("k, n, p", [(0, 20, 0.081), (1, 20, 0.081), (3, 20, 0.081), (5, 50, 0.128), (20, 50, 0.128)])
def test_prob_at_least_matches_scipy(dist, k, n, p):
    assert dist.prob_at_least(k, n, p) == pytest.approx(stats.binom.sf(k - 1, n, p), rel=1e-9, abs=1e-15)


@pytest.mark.parametrize("k, lam", [(0, 9.4), (9, 9.4), (25, 9.4), (0, 0.5), (300, 250.0)])
def test_poisson_pmf_matches_scipy(dist, k, lam):
    # λ = 250 với k = 300: tính thẳng lam**k / k! tràn số, phải làm trên log
    assert dist.poisson_pmf(k, lam) == pytest.approx(stats.poisson.pmf(k, lam), rel=1e-9, abs=1e-300)


@pytest.mark.parametrize("mean, median", [(159.83, 105.28), (12.56, 10.22), (2.0, 1.0)])
def test_lognormal_from_mean_median_roundtrip(dist, mean, median):
    mu, sigma = dist.lognormal_from_mean_median(mean, median)
    assert np.exp(mu) == pytest.approx(median)
    assert stats.lognorm(s=sigma, scale=np.exp(mu)).mean() == pytest.approx(mean)


def test_lognormal_rejects_mean_below_median(dist):
    with pytest.raises(ValueError):
        dist.lognormal_from_mean_median(100.0, 120.0)


def test_dispersion_index_poisson_near_one(dist):
    counts = np.random.default_rng(0).poisson(9.4, 20000)
    assert dist.dispersion_index(counts) == pytest.approx(1.0, abs=0.05)


def test_dispersion_index_uses_sample_variance(dist):
    counts = np.array([2, 4, 4, 4, 5, 5, 7, 9])
    assert dist.dispersion_index(counts) == pytest.approx(counts.var(ddof=1) / counts.mean())


def test_dispersion_index_detects_overdispersion(dist):
    rng = np.random.default_rng(1)
    rates = rng.gamma(shape=2.0, scale=5.0, size=20000)   # λ thay đổi theo giờ → hỗn hợp Poisson
    assert dist.dispersion_index(rng.poisson(rates)) > 3
