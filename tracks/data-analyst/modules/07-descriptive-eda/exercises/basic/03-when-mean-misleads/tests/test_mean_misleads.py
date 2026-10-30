import numpy as np
import pandas as pd
import pytest
from scipy import stats

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("mean_misleads.ipynb")


S = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 1000.0, np.nan])


def test_trimmed_mean(nb):
    # 10 giá trị không NaN, prop 0.1 → bỏ 1 ở mỗi đầu: mean của 2..9
    assert nb.trimmed_mean(S, 0.1) == pytest.approx(5.5)
    assert nb.trimmed_mean(S, 0.0) == pytest.approx(S.mean())
    assert nb.trimmed_mean(S, 0.15) == pytest.approx(5.5)          # floor(1.5) = 1
    assert nb.trimmed_mean(S, 0.2) == pytest.approx(stats.trim_mean(S.dropna(), 0.2))
    assert isinstance(nb.trimmed_mean(S, 0.1), float)


@pytest.mark.parametrize("prop", [-0.1, 0.5, 0.7])
def test_trimmed_mean_rejects_bad_prop(nb, prop):
    with pytest.raises(ValueError):
        nb.trimmed_mean(S, prop)


def test_winsorized_mean(nb):
    x = S.dropna()
    lo, hi = x.quantile(0.1), x.quantile(0.9)                        # 1.9 và 108.1 (nội suy tuyến tính)
    expected = x.clip(lo, hi).mean()
    assert nb.winsorized_mean(S, 0.1, 0.9) == pytest.approx(expected)
    assert nb.winsorized_mean(S, 0.0, 1.0) == pytest.approx(x.mean())
    assert nb.winsorized_mean(S) == pytest.approx(x.clip(x.quantile(0.05), x.quantile(0.95)).mean())
    with pytest.raises(ValueError):
        nb.winsorized_mean(S, 0.9, 0.1)


def test_share_within(nb):
    assert nb.share_within(S, 5.0, 2.0) == pytest.approx(0.5)        # 3,4,5,6,7 trên 10 giá trị, tính cả hai đầu
    assert nb.share_within(S, S.mean(), 50.0) == pytest.approx(0.0)  # mean 104.5: không ai ở gần
    assert isinstance(nb.share_within(S, 0.0, 1.0), float)


def test_mean_without_top(nb):
    assert nb.mean_without_top(S, 0) == pytest.approx(S.mean())
    assert nb.mean_without_top(S, 1) == pytest.approx(5.0)
    assert nb.mean_without_top(S, 9) == pytest.approx(1.0)
    for k in (-1, 10):
        with pytest.raises(ValueError):
            nb.mean_without_top(S, k)


def test_functions_do_not_mutate_input(nb):
    s = S.copy()
    nb.trimmed_mean(s, 0.1)
    nb.winsorized_mean(s)
    nb.share_within(s, 5, 1)
    nb.mean_without_top(s, 2)
    pd.testing.assert_series_equal(s, S)


def test_real_monthly_charges(nb):
    telco = pd.read_csv(ex.dataset("telco-churn") / "WA_Fn-UseC_-Telco-Customer-Churn.csv")
    mc = telco.MonthlyCharges
    assert nb.share_within(mc, mc.mean(), 5) == pytest.approx(0.0760, abs=1e-4)
    assert nb.share_within(mc, mc.median(), 5) == pytest.approx(0.1163, abs=1e-4)
    assert nb.trimmed_mean(mc, 0.1) == pytest.approx(64.9657, abs=1e-4)


def test_real_competition_distance(nb):
    stores = pd.read_csv(ex.dataset("store-sales") / "store.csv")
    cd = stores.CompetitionDistance
    assert nb.trimmed_mean(cd, 0.1) == pytest.approx(3774.96, abs=0.01)
    assert nb.winsorized_mean(cd) == pytest.approx(4932.89, abs=0.01)
    assert nb.mean_without_top(cd, 10) == pytest.approx(5020.34, abs=0.01)
