import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from linearmodels.iv import IV2SLS

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def iv():
    return ex.module("iv.py")


def simulate(n: int = 20000, strength: float = 0.5, seed: int = 0) -> pd.DataFrame:
    """ability (không quan sát được) làm tăng cả education lẫn wage. Tác động thật của education là 1.0."""
    rng = np.random.default_rng(seed)
    ability = rng.normal(size=n)
    region = rng.binomial(1, 0.5, n)
    z = rng.binomial(1, 0.5, n)
    educ = strength * z + 0.8 * ability + 0.3 * region + rng.normal(size=n)
    wage = 1.0 * educ + 1.5 * ability + 0.5 * region + rng.normal(size=n)
    return pd.DataFrame({"wage": wage, "educ": educ, "z": z, "region": region})


def test_wald_small_example(iv):
    df = pd.DataFrame({"y": [1.0, 3.0, 4.0, 8.0], "d": [0.0, 1.0, 1.0, 3.0], "z": [0, 0, 1, 1]})
    # (6 − 2) / (2 − 0.5)
    assert iv.wald_estimator(df, "y", "d", "z") == pytest.approx(4 / 1.5)


def test_first_stage_matches_statsmodels(iv):
    df = simulate(n=2000, seed=3)
    ref = sm.OLS(df.educ, sm.add_constant(df[["z", "region"]])).fit()
    coef, f = iv.first_stage(df, "educ", "z", ["region"])
    assert coef == pytest.approx(ref.params["z"], abs=1e-8)
    assert f == pytest.approx(ref.tvalues["z"] ** 2, abs=1e-6)


@pytest.mark.parametrize("exog", [["region"], []])
def test_two_sls_matches_linearmodels(iv, exog):
    df = simulate(n=2000, seed=4)
    ref = IV2SLS(df.wage, sm.add_constant(df[exog]) if exog else np.ones((len(df), 1)),
                 df.educ, df.z).fit(cov_type="unadjusted", debiased=True)
    coef, se = iv.two_sls(df, "wage", "educ", "z", exog)
    assert coef == pytest.approx(ref.params["educ"], abs=1e-8)
    assert se == pytest.approx(ref.std_errors["educ"], abs=1e-8)


def test_se_is_not_the_naive_second_stage(iv):
    df = simulate(n=2000, seed=5)
    fitted = sm.OLS(df.educ, sm.add_constant(df[["z", "region"]])).fit().fittedvalues
    naive = sm.OLS(df.wage, sm.add_constant(pd.DataFrame({"educ_hat": fitted, "region": df.region}))).fit()
    coef, se = iv.two_sls(df, "wage", "educ", "z", ["region"])
    assert coef == pytest.approx(naive.params["educ_hat"], abs=1e-8)   # cùng hệ số...
    assert abs(se - naive.bse["educ_hat"]) > 0.01                      # ...nhưng SE khác


@pytest.mark.parametrize("seed", range(5))
def test_two_sls_removes_ability_bias(iv, seed):
    df = simulate(seed=seed)
    ols = sm.OLS(df.wage, sm.add_constant(df[["educ", "region"]])).fit().params["educ"]
    coef, se = iv.two_sls(df, "wage", "educ", "z", ["region"])
    assert ols > 1.5                                   # OLS lệch lên vì ability
    assert coef == pytest.approx(1.0, abs=0.25)
    assert abs(coef - 1.0) < 4 * se


def test_weak_instrument_has_small_f(iv):
    strong = iv.first_stage(simulate(strength=0.5, seed=1), "educ", "z", ["region"])[1]
    weak = iv.first_stage(simulate(n=2000, strength=0.05, seed=1), "educ", "z", ["region"])[1]
    assert strong > 100
    assert weak < 10


def test_real_card(iv):
    df = pd.read_csv(ex.dataset("card") / "card.csv")
    exog = ["exper", "expersq", "black", "south", "smsa", "smsa66"] + [f"reg66{i}" for i in range(2, 10)]
    assert iv.wald_estimator(df, "lwage", "educ", "nearc4") == pytest.approx(0.1881, abs=5e-4)
    coef_fs, f = iv.first_stage(df, "educ", "nearc4", exog)
    assert coef_fs == pytest.approx(0.320, abs=1e-3)
    assert f == pytest.approx(13.26, abs=0.01)
    coef, se = iv.two_sls(df, "lwage", "educ", "nearc4", exog)
    assert coef == pytest.approx(0.1315, abs=5e-4)
    assert se == pytest.approx(0.0550, abs=5e-4)
