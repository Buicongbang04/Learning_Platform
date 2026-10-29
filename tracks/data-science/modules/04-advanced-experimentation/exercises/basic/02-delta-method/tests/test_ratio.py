import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def rt():
    return ex.module("ratio.py")


def make_users(n: int, seed: int, ctr: float = 0.10, concentration: float = 4.0):
    """Mỗi user có số lượt xem khác nhau và CTR riêng: click của cùng user tương quan với nhau."""
    rng = np.random.default_rng(seed)
    views = 1 + rng.poisson(9, n)
    user_ctr = rng.beta(ctr * concentration, (1 - ctr) * concentration, n)
    clicks = rng.binomial(views, user_ctr)
    return clicks.astype(float), views.astype(float)


def bootstrap_se(clicks, views, n_boot=600, seed=0):
    rng = np.random.default_rng(seed)
    n = len(clicks)
    idx = rng.integers(0, n, (n_boot, n))
    return np.std(clicks[idx].sum(1) / views[idx].sum(1), ddof=1)


def test_ratio_value(rt):
    num = np.array([1.0, 0.0, 3.0, 2.0])
    den = np.array([4.0, 2.0, 5.0, 9.0])
    ratio, var = rt.ratio_delta(num, den)
    assert ratio == pytest.approx(6 / 20)   # tổng trên tổng, không phải trung bình các tỉ lệ
    assert var > 0


def test_reduces_to_mean_variance_when_den_is_one(rt):
    rng = np.random.default_rng(1)
    num = rng.normal(5, 2, 500)
    ratio, var = rt.ratio_delta(num, np.ones(500))
    assert ratio == pytest.approx(num.mean())
    assert var == pytest.approx(num.var(ddof=1) / 500)


def test_delta_matches_bootstrap(rt):
    clicks, views = make_users(3000, seed=2)
    _, var = rt.ratio_delta(clicks, views)
    assert np.sqrt(var) == pytest.approx(bootstrap_se(clicks, views), rel=0.1)


def test_naive_binomial_se_is_too_small_with_clustering(rt):
    clicks, views = make_users(3000, seed=3)
    _, var = rt.ratio_delta(clicks, views)
    naive = rt.naive_binomial_se(clicks, views)
    assert naive == pytest.approx(np.sqrt(0.1 * 0.9 / views.sum()), rel=0.1)
    assert naive < 0.75 * np.sqrt(var)


def test_ratio_diff_ci_structure(rt):
    ca, va = make_users(4000, seed=4, ctr=0.10)
    cb, vb = make_users(4000, seed=5, ctr=0.12)
    out = rt.ratio_diff_ci(ca, va, cb, vb)
    assert out["diff"] == pytest.approx(cb.sum() / vb.sum() - ca.sum() / va.sum())
    assert out["ci_low"] < out["diff"] < out["ci_high"]
    assert out["ci_low"] > 0 and out["p_value"] < 0.01
    assert out["ci_high"] - out["ci_low"] == pytest.approx(2 * 1.959964 * out["se"], rel=1e-4)


def test_aa_false_positive_rate(rt):
    sims = 400
    delta_hits = naive_hits = 0
    for s in range(sims):
        ca, va = make_users(800, seed=10_000 + 2 * s)
        cb, vb = make_users(800, seed=10_001 + 2 * s)
        delta_hits += rt.ratio_diff_ci(ca, va, cb, vb)["p_value"] < 0.05
        diff = cb.sum() / vb.sum() - ca.sum() / va.sum()
        naive_se = np.hypot(rt.naive_binomial_se(ca, va), rt.naive_binomial_se(cb, vb))
        naive_hits += abs(diff / naive_se) > 1.96
    assert 0.025 <= delta_hits / sims <= 0.085
    assert naive_hits / sims > 0.15   # coi mỗi lượt xem độc lập: báo động nhầm gấp nhiều lần 5%


def test_relative_lift(rt):
    ca, va = make_users(5000, seed=6, ctr=0.10)
    cb, vb = make_users(5000, seed=7, ctr=0.11)
    out = rt.relative_lift_ci(ca, va, cb, vb)
    ra, rb = ca.sum() / va.sum(), cb.sum() / vb.sum()
    assert out["lift"] == pytest.approx(rb / ra - 1)
    assert out["ci_low"] < out["lift"] < out["ci_high"]
    # so với bootstrap của chính tỉ số rb / ra
    rng = np.random.default_rng(0)
    ia = rng.integers(0, 5000, (500, 5000))
    ib = rng.integers(0, 5000, (500, 5000))
    boot = (cb[ib].sum(1) / vb[ib].sum(1)) / (ca[ia].sum(1) / va[ia].sum(1)) - 1
    assert out["se"] == pytest.approx(np.std(boot, ddof=1), rel=0.12)
