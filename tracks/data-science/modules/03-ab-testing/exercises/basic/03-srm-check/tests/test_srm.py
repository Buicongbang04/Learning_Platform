import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def srm():
    return ex.module("srm.py")


def test_perfect_split_has_pvalue_one(srm):
    assert srm.srm_pvalue([50000, 50000], [1, 1]) == pytest.approx(1.0)


def test_cookie_cats_counts(srm):
    assert srm.srm_pvalue([44700, 45489], [0.5, 0.5]) == pytest.approx(0.008608, abs=1e-5)


def test_threshold_must_be_chosen_in_advance(srm):
    counts = [44700, 45489]
    assert srm.has_srm(counts, [0.5, 0.5]) is False            # ngưỡng mặc định 0.001
    assert srm.has_srm(counts, [0.5, 0.5], threshold=0.01) is True


def test_ratios_are_normalised(srm):
    assert srm.srm_pvalue([9000, 1000], [90, 10]) == pytest.approx(srm.srm_pvalue([9000, 1000], [0.9, 0.1]))
    assert srm.srm_pvalue([9000, 1000], [0.9, 0.1]) == pytest.approx(1.0)


def test_three_arms(srm):
    assert srm.has_srm([3300, 3300, 3400], [1, 1, 1]) is False
    assert srm.has_srm([3300, 3300, 3800], [1, 1, 1]) is True


def test_obvious_mismatch(srm):
    assert srm.has_srm([5000, 4500], [1, 1]) is True


def test_unequal_design_without_mismatch(srm):
    assert srm.has_srm([9020, 980], [0.9, 0.1]) is False


def test_aa_false_alarm_rate_matches_threshold(srm):
    rng = np.random.default_rng(7)
    sims = 2000
    a = rng.binomial(20000, 0.5, sims)
    alarms = np.mean([srm.has_srm([int(x), 20000 - int(x)], [1, 1], threshold=0.05) for x in a])
    assert 0.035 <= alarms <= 0.065


def test_real_cookie_cats():
    path = ex.dataset("cookie-cats") / "cookie_cats.csv"
    counts = pd.read_csv(path)["version"].value_counts().sort_index()
    srm = ex.module("srm.py")
    assert srm.srm_pvalue(counts.tolist(), [1, 1]) == pytest.approx(0.008608, abs=1e-5)
