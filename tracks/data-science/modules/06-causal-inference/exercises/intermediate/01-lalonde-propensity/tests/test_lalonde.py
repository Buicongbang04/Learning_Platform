import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("lalonde.ipynb")


def simulate(n: int = 20000, seed: int = 0) -> pd.DataFrame:
    """x1 làm tăng cả xác suất tham gia lẫn kết quả; tác động thay đổi theo x1 nên ATT ≠ ATE."""
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.binomial(1, 0.4, n)
    p = 1 / (1 + np.exp(-(-1.0 + 1.2 * x1 + 0.8 * x2)))
    treat = rng.binomial(1, p)
    effect = 2.0 + 1.0 * x1
    y = 3.0 * x1 + 1.5 * x2 + effect * treat + rng.normal(0, 1, n)
    return pd.DataFrame({"x1": x1, "x2": x2, "treat": treat, "y": y, "effect": effect})


def true_att(df: pd.DataFrame) -> float:
    return float(df.loc[df.treat == 1, "effect"].mean())


def test_diff_in_means(nb):
    df = pd.DataFrame({"treat": [1, 1, 0, 0, 0], "re78": [10.0, 20.0, 3.0, 6.0, 9.0]})
    assert nb.diff_in_means(df) == pytest.approx(9.0)


def test_smd_unweighted_and_weighted(nb):
    df = pd.DataFrame({"treat": [1, 1, 1, 0, 0, 0], "a": [1.0, 2.0, 3.0, 2.0, 3.0, 4.0]})
    # hiệu trung bình −1, phương sai mỗi nhóm 1 → SMD = −1
    assert nb.smd(df, ["a"])["a"] == pytest.approx(-1.0)
    w = np.array([1, 1, 1, 0.0, 1, 1])     # control có trọng số: trung bình 3.5, mẫu số vẫn không trọng số
    assert nb.smd(df, ["a"], weights=w)["a"] == pytest.approx(-1.5)


def test_propensity_matches_statsmodels(nb):
    df = simulate(n=3000, seed=1)
    ps = nb.propensity_scores(df, ["x1", "x2"])
    X = sm.add_constant(df[["x1", "x2"]])
    ref = sm.Logit(df.treat, X).fit(disp=0).predict(X)
    assert np.allclose(ps, ref, atol=1e-5)


def test_att_weights_and_ess(nb):
    w = nb.att_weights(np.array([0.5, 0.2, 0.8]), np.array([1, 0, 0]))
    assert w == pytest.approx([1.0, 0.25, 4.0])
    assert nb.effective_sample_size(np.ones(10)) == pytest.approx(10)
    assert nb.effective_sample_size(np.array([1.0, 0, 0, 0])) == pytest.approx(1)
    assert nb.effective_sample_size(np.array([3.0, 1.0])) == pytest.approx(1.6)


@pytest.mark.parametrize("seed", range(5))
def test_ipw_att_recovers_truth_and_balances(nb, seed):
    df = simulate(seed=seed)
    naive = nb.diff_in_means(df, outcome="y")
    ps = nb.propensity_scores(df, ["x1", "x2"])
    att = nb.ipw_att(df, ps, outcome="y")
    assert naive - true_att(df) > 2.0                    # ngây thơ lệch rất xa
    assert att == pytest.approx(true_att(df), abs=0.15)
    balance = nb.smd(df, ["x1", "x2"], weights=nb.att_weights(ps, df.treat.to_numpy()))
    assert balance.abs().max() < 0.05


def test_nn_match_small_example(nb):
    df = pd.DataFrame({"treat": [1, 1, 0, 0, 0], "re78": [10.0, 7.0, 4.0, 1.0, 5.0]})
    ps = np.array([0.8, 0.3, 0.75, 0.2, 0.35])
    # treated 0.8 ↔ control 0.75 (y = 4); treated 0.3 ↔ control 0.35 (y = 5) → ATT = (6 + 2) / 2
    assert nb.nn_match_att(df, ps) == pytest.approx(4.0)


@pytest.mark.parametrize("seed", range(3))
def test_nn_match_recovers_truth(nb, seed):
    df = simulate(n=6000, seed=seed)
    ps = nb.propensity_scores(df, ["x1", "x2"])
    assert nb.nn_match_att(df, ps, outcome="y") == pytest.approx(true_att(df), abs=0.25)


def test_real_lalonde(nb):
    folder = ex.dataset("lalonde")
    nsw = pd.read_stata(folder / "nsw_dw.dta")
    psid = pd.read_stata(folder / "psid_controls.dta")
    obs = pd.concat([nsw[nsw.treat == 1], psid], ignore_index=True)
    assert nb.diff_in_means(nsw) == pytest.approx(1794.34, abs=0.01)
    assert nb.diff_in_means(obs) == pytest.approx(-15204.78, abs=0.01)
    assert nb.smd(obs, nb.COVARIATES)["re75"] < -1.5
    ps = nb.propensity_scores(obs, nb.COVARIATES)
    assert nb.ipw_att(obs, ps) == pytest.approx(1758.9, abs=20)
    assert nb.nn_match_att(obs, ps) == pytest.approx(2125.7, abs=20)
    w = nb.att_weights(ps, obs.treat.to_numpy())
    assert nb.effective_sample_size(w[obs.treat.to_numpy() == 0]) == pytest.approx(42.6, abs=1)
