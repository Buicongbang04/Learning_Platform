import numpy as np
import pytest
from statsmodels.stats.multitest import multipletests

from testkit import Exercise

ex = Exercise(__file__)

VECTORS = [
    [0.01, 0.02, 0.03, 0.04, 0.05],
    [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216],
    [0.04, 0.001, 0.04, 0.3, 0.012, 0.012],          # trùng nhau, không theo thứ tự
    [0.5, 0.7, 0.9],
    [0.0001],
]
METHODS = [("bonferroni", "bonferroni"), ("holm", "holm"), ("benjamini_hochberg", "fdr_bh")]


@pytest.fixture(scope="module")
def mt():
    return ex.module("multiple.py")


@pytest.mark.parametrize("name, sm_method", METHODS)
@pytest.mark.parametrize("pvals", VECTORS)
def test_matches_statsmodels(mt, name, sm_method, pvals):
    expected = multipletests(pvals, alpha=0.05, method=sm_method)[0].tolist()
    result = getattr(mt, name)(pvals)
    assert result == expected
    assert all(isinstance(r, bool) for r in result)


@pytest.mark.parametrize("name, sm_method", METHODS)
def test_alpha_parameter(mt, name, sm_method):
    pvals = VECTORS[1]
    assert getattr(mt, name)(pvals, alpha=0.1) == multipletests(pvals, alpha=0.1, method=sm_method)[0].tolist()


def test_holm_at_least_as_powerful_as_bonferroni(mt):
    rng = np.random.default_rng(0)
    for _ in range(200):
        pvals = rng.uniform(0, 0.1, 8).tolist()
        bonf, holm = mt.bonferroni(pvals), mt.holm(pvals)
        assert all(h or not b for b, h in zip(bonf, holm))


def test_fwer_under_global_null(mt):
    rng = np.random.default_rng(1)
    sims = 2000
    pvals = rng.uniform(size=(sims, 10))      # 10 metric, không metric nào có tác động thật
    any_unadjusted = np.mean((pvals < 0.05).any(axis=1))
    any_holm = np.mean([any(mt.holm(row.tolist())) for row in pvals])
    assert any_unadjusted > 0.3
    assert any_holm <= 0.06
