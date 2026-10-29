import time

import numpy as np
import pytest
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def rb():
    return ex.module("robust.py")


def hetero(seed: int, n: int = 400):
    """y = 1 + 2x + e, sd(e) tăng mạnh theo |x|: heteroskedastic."""
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    y = 1 + 2 * x + rng.normal(size=n) * (0.3 + 1.5 * x**2)
    return sm.add_constant(x), y


@pytest.mark.parametrize("kind", ["HC0", "HC1", "HC3"])
@pytest.mark.parametrize("seed", [0, 1])
def test_hc_cov_matches_statsmodels(rb, kind, seed):
    X, y = hetero(seed)
    ref = sm.OLS(y, X).fit()
    cov = rb.hc_cov(X, ref.resid, kind=kind)
    assert np.asarray(cov) == pytest.approx(getattr(ref, f"cov_{kind}"), abs=1e-8)
    assert np.asarray(rb.robust_se(X, y, kind=kind)) == pytest.approx(np.sqrt(np.diag(getattr(ref, f"cov_{kind}"))), abs=1e-8)


def test_hc_cov_multiple_regressors(rb):
    rng = np.random.default_rng(5)
    X = sm.add_constant(rng.normal(size=(300, 3)))
    y = X @ [1, 0.5, -1, 2] + rng.standard_t(3, 300) * np.exp(X[:, 1])
    ref = sm.OLS(y, X).fit()
    assert np.asarray(rb.hc_cov(X, ref.resid, "HC3")) == pytest.approx(ref.cov_HC3, abs=1e-8)


def test_unknown_kind_raises(rb):
    X, y = hetero(0)
    with pytest.raises(ValueError):
        rb.hc_cov(X, y - y.mean(), kind="HC9")


def test_large_n_is_fast(rb):
    X, y = hetero(1, n=200_000)
    start = time.perf_counter()
    rb.robust_se(X, y)
    assert time.perf_counter() - start < 5


def fan(seed: int, n: int = 400):
    """x dương, sd(e) tăng tuyến tính theo x: hình phễu, đúng dạng Breusch-Pagan bắt được."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 3, n)
    y = 1 + 2 * x + rng.normal(size=n) * (0.2 + x)
    return sm.add_constant(x), y


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_breusch_pagan_matches_statsmodels(rb, seed):
    X, y = fan(seed)
    resid = sm.OLS(y, X).fit().resid
    lm, p = rb.breusch_pagan(X, resid)
    lm_ref, p_ref, _, _ = het_breuschpagan(resid, X)
    assert lm == pytest.approx(lm_ref, abs=1e-8)
    assert p == pytest.approx(p_ref, abs=1e-8)
    assert p < 0.01


def test_coverage_hc3_vs_classic(rb):
    """Mô phỏng 600 lần: CI 95% HC3 gần đúng, CI cổ điển quá hẹp."""
    rng = np.random.default_rng(42)
    hit_hc3 = hit_classic = 0
    reps, n = 600, 200
    for _ in range(reps):
        x = rng.normal(size=n)
        y = 1 + 2 * x + rng.normal(size=n) * (0.3 + 1.5 * x**2)
        X = sm.add_constant(x)
        fit = sm.OLS(y, X).fit()
        se_hc3 = np.asarray(rb.robust_se(X, y, "HC3"))[1]
        hit_hc3 += abs(fit.params[1] - 2) < 1.96 * se_hc3
        hit_classic += abs(fit.params[1] - 2) < 1.96 * fit.bse[1]
    assert 0.92 <= hit_hc3 / reps <= 0.97
    assert hit_classic / reps < 0.90
