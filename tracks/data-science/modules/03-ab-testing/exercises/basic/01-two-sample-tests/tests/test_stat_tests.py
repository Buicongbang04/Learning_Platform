import numpy as np
import pytest
from scipy import stats
from statsmodels.stats.proportion import confint_proportions_2indep, proportions_ztest

from testkit import Exercise

ex = Exercise(__file__)

CASES = [
    (8502, 44700, 8279, 45489),     # Cookie Cats retention_7: gate_30 (A) vs gate_40 (B)
    (17489, 145274, 17264, 145310),  # ab_data sau khi làm sạch: control vs treatment
    (120, 1000, 150, 1000),
]


@pytest.fixture(scope="module")
def st():
    return ex.module("stat_tests.py")


@pytest.mark.parametrize("x_a, n_a, x_b, n_b", CASES)
def test_two_proportion_ztest_matches_statsmodels(st, x_a, n_a, x_b, n_b):
    z, p = st.two_proportion_ztest(x_a, n_a, x_b, n_b)
    z_ref, p_ref = proportions_ztest(count=[x_b, x_a], nobs=[n_b, n_a])
    assert z == pytest.approx(z_ref, abs=1e-9)
    assert p == pytest.approx(p_ref, abs=1e-9)


def test_z_sign_follows_b_minus_a(st):
    z, _ = st.two_proportion_ztest(100, 1000, 150, 1000)
    assert z > 0


@pytest.mark.parametrize("x_a, n_a, x_b, n_b", CASES)
def test_diff_proportion_ci_matches_statsmodels(st, x_a, n_a, x_b, n_b):
    lo, hi = st.diff_proportion_ci(x_a, n_a, x_b, n_b)
    lo_ref, hi_ref = confint_proportions_2indep(x_b, n_b, x_a, n_a, method="wald", compare="diff")
    assert (lo, hi) == pytest.approx((lo_ref, hi_ref), abs=1e-9)


def test_diff_proportion_ci_respects_alpha(st):
    lo95, hi95 = st.diff_proportion_ci(120, 1000, 150, 1000)
    lo99, hi99 = st.diff_proportion_ci(120, 1000, 150, 1000, alpha=0.01)
    assert lo99 < lo95 < hi95 < hi99


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_welch_ttest_matches_scipy(st, seed):
    rng = np.random.default_rng(seed)
    a = rng.exponential(10, 800)          # doanh thu lệch phải, hai nhóm khác variance
    b = rng.exponential(12, 1200)
    t, p = st.welch_ttest(a, b)
    ref = stats.ttest_ind(b, a, equal_var=False)
    assert t == pytest.approx(ref.statistic, abs=1e-9)
    assert p == pytest.approx(ref.pvalue, abs=1e-9)


def test_welch_differs_from_student_when_variances_differ(st):
    rng = np.random.default_rng(3)
    a = rng.normal(0, 1, 50)
    b = rng.normal(0.3, 5, 500)
    _, p_welch = st.welch_ttest(a, b)
    _, p_student = stats.ttest_ind(b, a, equal_var=True)
    assert p_welch != pytest.approx(p_student, abs=1e-3)
