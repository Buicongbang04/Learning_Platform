import numpy as np
import pytest
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def ci():
    return ex.module("ci.py")


@pytest.mark.parametrize("seed, n", [(0, 8), (1, 50), (2, 2000)])
def test_mean_ci_matches_scipy(ci, seed, n):
    x = np.random.default_rng(seed).lognormal(2.4, 0.7, n)
    lo, hi = ci.mean_ci(x)
    ref = stats.t.interval(0.95, n - 1, loc=x.mean(), scale=stats.sem(x))
    assert (lo, hi) == pytest.approx(ref, abs=1e-9)


def test_mean_ci_wider_with_smaller_alpha(ci):
    x = np.random.default_rng(3).normal(10, 2, 40)
    lo95, hi95 = ci.mean_ci(x)
    lo99, hi99 = ci.mean_ci(x, alpha=0.01)
    assert lo99 < lo95 < hi95 < hi99


CASES = [(1, 11), (24, 105), (0, 7), (7, 7), (12272, 95824)]


@pytest.mark.parametrize("k, n", CASES)
def test_wald_matches_statsmodels(ci, k, n):
    ref = proportion_confint(k, n, alpha=0.05, method="normal")
    assert ci.wald_ci(k, n) == pytest.approx(ref, abs=1e-9)


@pytest.mark.parametrize("k, n", CASES)
def test_wilson_matches_statsmodels(ci, k, n):
    ref = proportion_confint(k, n, alpha=0.05, method="wilson")
    assert ci.wilson_ci(k, n) == pytest.approx(ref, abs=1e-9)


def test_wilson_respects_alpha(ci):
    ref = proportion_confint(24, 105, alpha=0.1, method="wilson")
    assert ci.wilson_ci(24, 105, alpha=0.1) == pytest.approx(ref, abs=1e-9)


def test_wald_collapses_at_zero_but_wilson_does_not(ci):
    lo, hi = ci.wald_ci(0, 7)
    assert lo == pytest.approx(0) and hi == pytest.approx(0)
    lo, hi = ci.wilson_ci(0, 7)
    assert lo == pytest.approx(0, abs=1e-12) and hi > 0.3


def test_coverage_wald_is_poor_for_rare_events(ci):
    # độ phủ chính xác (tính bằng tổng xác suất Binomial): Wald 0.635, Wilson 0.922
    assert 0.60 <= ci.coverage(ci.wald_ci, p=0.02, n=50, n_sims=20000, seed=0) <= 0.67
    assert 0.90 <= ci.coverage(ci.wilson_ci, p=0.02, n=50, n_sims=20000, seed=0) <= 0.95


def test_coverage_both_fine_with_large_n(ci):
    for fn in (ci.wald_ci, ci.wilson_ci):
        assert 0.93 <= ci.coverage(fn, p=0.128, n=400, n_sims=20000, seed=1) <= 0.97


def test_coverage_reproducible(ci):
    a = ci.coverage(ci.wald_ci, p=0.1, n=30, n_sims=2000, seed=5)
    assert a == ci.coverage(ci.wald_ci, p=0.1, n=30, n_sims=2000, seed=5)
