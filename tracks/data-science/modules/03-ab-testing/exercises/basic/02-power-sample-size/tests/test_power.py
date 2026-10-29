import numpy as np
import pytest
from scipy.stats import norm
from statsmodels.stats.power import TTestIndPower

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def pw():
    return ex.module("power.py")


def test_sample_size_proportions_known_value(pw):
    assert pw.sample_size_proportions(0.10, 0.01) == 14749


def test_sample_size_is_integer_and_ceiled(pw):
    n = pw.sample_size_proportions(0.128, -0.01)   # baseline review xấu của Olist, muốn giảm 1 điểm
    assert isinstance(n, int)
    assert n == 16930


def test_sample_size_shrinks_as_mde_grows(pw):
    sizes = [pw.sample_size_proportions(0.10, m) for m in (0.005, 0.01, 0.02, 0.04)]
    assert sizes == sorted(sizes, reverse=True)
    assert sizes[0] / sizes[1] == pytest.approx(4, rel=0.05)   # MDE giảm một nửa → cần ~4 lần mẫu


def test_more_power_or_stricter_alpha_needs_more_samples(pw):
    base = pw.sample_size_proportions(0.10, 0.01)
    assert pw.sample_size_proportions(0.10, 0.01, power=0.9) > base
    assert pw.sample_size_proportions(0.10, 0.01, alpha=0.01) > base


def test_mde_is_inverse_of_sample_size(pw):
    n = pw.sample_size_proportions(0.10, 0.02)
    assert pw.mde_proportions(0.10, n) == pytest.approx(0.02, rel=0.01)


def test_mde_shrinks_with_more_samples(pw):
    assert pw.mde_proportions(0.10, 40000) < pw.mde_proportions(0.10, 10000)


def test_simulated_power_is_about_80_percent(pw):
    p1, mde = 0.20, 0.03
    n = pw.sample_size_proportions(p1, mde)
    rng = np.random.default_rng(42)
    sims = 3000
    x_a = rng.binomial(n, p1, sims)
    x_b = rng.binomial(n, p1 + mde, sims)
    pool = (x_a + x_b) / (2 * n)
    z = (x_b - x_a) / n / np.sqrt(pool * (1 - pool) * 2 / n)
    rejected = np.mean(2 * norm.sf(np.abs(z)) < 0.05)
    assert 0.77 <= rejected <= 0.83


def test_sample_size_means_matches_statsmodels(pw):
    ref = TTestIndPower().solve_power(effect_size=1 / 10, alpha=0.05, power=0.8)
    assert pw.sample_size_means(sigma=10, mde_abs=1) == pytest.approx(ref, rel=0.02)
