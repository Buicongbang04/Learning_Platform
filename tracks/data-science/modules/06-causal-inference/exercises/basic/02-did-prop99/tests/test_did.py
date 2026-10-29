import numpy as np
import pandas as pd
import pytest
import statsmodels.formula.api as smf

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def did():
    return ex.module("did.py")


def make_panel(effect: float = -5.0, trend_gap: float = 0.0, n_units: int = 30, seed: int = 0) -> pd.DataFrame:
    """Panel năm 2000–2011, can thiệp từ 2006 cho 10 đơn vị đầu. trend_gap: nhóm treated dốc thêm mỗi năm."""
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(n_units):
        treated = int(u < 10)
        level = rng.normal(100, 10)
        for year in range(2000, 2012):
            post = int(year >= 2006)
            y = level - 1.5 * (year - 2000) + trend_gap * treated * (year - 2000) + effect * treated * post
            rows.append({"unit": f"u{u}", "year": year, "treated": treated, "post": post,
                         "y": y + rng.normal(0, 1)})
    return pd.DataFrame(rows)


def test_did_2x2_is_difference_of_differences(did):
    df = pd.DataFrame({
        "y": [10, 12, 20, 25, 11, 13, 21, 24],
        "treated": [0, 0, 1, 1, 0, 0, 1, 1],
        "post": [0, 1, 0, 1, 0, 1, 0, 1],
    })
    # control: 10.5 → 12.5 (+2); treated: 20.5 → 24.5 (+4) → DiD = 2
    assert did.did_2x2(df, "y", "treated", "post") == pytest.approx(2.0)


@pytest.mark.parametrize("seed", range(5))
def test_did_recovers_effect_under_parallel_trends(did, seed):
    df = make_panel(seed=seed)
    assert did.did_2x2(df, "y", "treated", "post") == pytest.approx(-5.0, abs=1.0)
    coef, se = did.did_regression(df, "y", "unit", "year", "treated", "post")
    assert coef == pytest.approx(-5.0, abs=1.0)
    assert 0 < se < 1


def test_did_regression_matches_statsmodels(did):
    df = make_panel(seed=7)
    ref = smf.ols("y ~ C(unit) + C(year) + treated:post", df).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(df["unit"])[0]})
    coef, se = did.did_regression(df, "y", "unit", "year", "treated", "post")
    assert coef == pytest.approx(ref.params["treated:post"], abs=1e-8)
    assert se == pytest.approx(ref.bse["treated:post"], abs=1e-8)


def test_pretrend_gap_detects_diverging_trends(did):
    parallel = make_panel(seed=1)
    diverging = make_panel(trend_gap=-1.0, seed=1)
    assert abs(did.pretrend_slope_gap(parallel, "y", "year", "treated", "post")) < 0.3
    assert did.pretrend_slope_gap(diverging, "y", "year", "treated", "post") == pytest.approx(-1.0, abs=0.3)
    # DiD lệch khi trend không song song: phần dốc thêm sau 2006 bị tính nhầm là tác động
    assert did.did_2x2(diverging, "y", "treated", "post") < -9


def test_real_prop99(did):
    df = pd.read_csv(ex.dataset("prop99") / "smoking_data.csv")
    df["year"] = df["year"].astype(int)
    df["treated"] = (df["state"] == "California").astype(int)
    df["post"] = (df["year"] >= 1989).astype(int)
    assert did.did_2x2(df, "cigsale", "treated", "post") == pytest.approx(-27.35, abs=0.01)
    coef, se = did.did_regression(df, "cigsale", "state", "year", "treated", "post")
    assert coef == pytest.approx(-27.35, abs=0.01)
    assert se == pytest.approx(2.85, abs=0.01)
    assert did.pretrend_slope_gap(df, "cigsale", "year", "treated", "post") == pytest.approx(-1.23, abs=0.01)
