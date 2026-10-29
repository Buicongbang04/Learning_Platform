import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def cp():
    return ex.module("cuped.py")


def make_experiment(n: int, rho: float, effect: float, seed: int):
    """x là metric trước thí nghiệm, y là metric trong thí nghiệm, corr(x, y) ≈ rho ở nhóm control."""
    rng = np.random.default_rng(seed)
    x = rng.normal(100, 20, n)
    noise = rng.normal(0, 20, n)
    treat = rng.permutation(np.arange(n) % 2 == 1)
    y = 50 + rho * (x - 100) + np.sqrt(1 - rho**2) * noise + effect * treat
    return y, x, treat


def test_theta_is_cov_over_var(cp):
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 5000)
    y = 2 * x + rng.normal(0, 1, 5000)
    assert cp.cuped_theta(y, x) == pytest.approx(np.cov(y, x)[0, 1] / np.var(x, ddof=1))
    assert cp.cuped_theta(y, x) == pytest.approx(2, abs=0.05)


def test_adjust_keeps_mean_and_removes_rho_squared(cp):
    y, x, _ = make_experiment(20000, 0.7, 0.0, seed=1)
    adjusted = cp.cuped_adjust(y, x)
    assert adjusted.shape == y.shape
    assert adjusted.mean() == pytest.approx(y.mean())
    rho = np.corrcoef(y, x)[0, 1]
    assert cp.variance_reduction(y, x) == pytest.approx(rho**2, rel=1e-6)
    assert 1 - adjusted.var() / y.var() == pytest.approx(rho**2, rel=1e-6)


def test_adjust_accepts_given_theta(cp):
    y, x, _ = make_experiment(1000, 0.5, 0.0, seed=2)
    assert np.allclose(cp.cuped_adjust(y, x, theta=0.0), y)
    assert np.allclose(cp.cuped_adjust(y, x, theta=1.0), y - (x - x.mean()))


def test_effect_keys_and_raw_numbers(cp):
    y, x, treat = make_experiment(4000, 0.8, 1.0, seed=3)
    out = cp.cuped_effect(y, x, treat)
    assert {"diff", "se", "ci_low", "ci_high", "diff_raw", "se_raw"} <= set(out)
    assert out["diff_raw"] == pytest.approx(y[treat].mean() - y[~treat].mean())
    se_raw = np.sqrt(y[treat].var(ddof=1) / treat.sum() + y[~treat].var(ddof=1) / (~treat).sum())
    assert out["se_raw"] == pytest.approx(se_raw)
    assert out["ci_low"] < out["diff"] < out["ci_high"]
    assert out["ci_high"] - out["ci_low"] == pytest.approx(2 * 1.959964 * out["se"], rel=1e-4)
    # rho = 0.8 → SE còn khoảng sqrt(1 - 0.64) = 0.6 lần
    assert out["se"] / out["se_raw"] == pytest.approx(0.6, abs=0.05)


def test_cuped_is_unbiased_and_tighter_across_experiments(cp):
    diffs, raws = [], []
    for seed in range(300):
        y, x, treat = make_experiment(4000, 0.8, 1.0, seed=100 + seed)
        out = cp.cuped_effect(y, x, treat)
        diffs.append(out["diff"])
        raws.append(out["diff_raw"])
    assert np.mean(diffs) == pytest.approx(1.0, abs=0.1)
    assert np.std(diffs) < 0.7 * np.std(raws)


def test_ci_coverage_is_about_95_percent(cp):
    hits = 0
    for seed in range(400):
        y, x, treat = make_experiment(1000, 0.6, 2.0, seed=1000 + seed)
        out = cp.cuped_effect(y, x, treat)
        hits += out["ci_low"] <= 2.0 <= out["ci_high"]
    assert 0.91 <= hits / 400 <= 0.985


def test_post_treatment_covariate_destroys_the_effect(cp):
    # Lỗi kinh điển: "covariate" đo SAU khi can thiệp, nên chứa chính tác động.
    rng = np.random.default_rng(4)
    n = 20000
    treat = rng.permutation(np.arange(n) % 2 == 1)
    y = rng.normal(50, 10, n) + 2.0 * treat
    x_post = y + rng.normal(0, 2, n)
    out = cp.cuped_effect(y, x_post, treat)
    assert abs(out["diff"]) < 0.5 < abs(out["diff_raw"])


def test_n_after_cuped(cp):
    assert cp.n_after_cuped(10000, 0.5) == 7500
    assert cp.n_after_cuped(16930, 0.3) == 15407
    assert cp.n_after_cuped(16930, 0.0) == 16930
    assert isinstance(cp.n_after_cuped(100, 0.5), int)
