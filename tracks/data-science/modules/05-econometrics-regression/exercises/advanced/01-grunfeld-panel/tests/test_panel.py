import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from linearmodels.panel import PanelOLS, RandomEffects

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def panel():
    return ex.module("panel.py")


def grunfeld() -> pd.DataFrame:
    g = sm.datasets.grunfeld.load_pandas().data
    return g.assign(year=g.year.astype(int))


def simulate(seed: int, n_entity: int = 300, n_time: int = 4, rho: float = 1.0) -> pd.DataFrame:
    """y = alpha_i + 0.5 x + e; x = rho * alpha_i + nhiễu. rho > 0: alpha tương quan với x."""
    rng = np.random.default_rng(seed)
    entity = np.repeat(np.arange(n_entity), n_time)
    alpha = rng.normal(0, 1, n_entity)[entity]
    x = rho * alpha + rng.normal(0, 1, len(entity))
    z = rng.normal(0, 1, len(entity))
    y = alpha + 0.5 * x - 0.3 * z + rng.normal(0, 1, len(entity))
    return pd.DataFrame({"entity": entity, "time": np.tile(np.arange(n_time), n_entity), "x": x, "z": z, "y": y})


def fe_re(df, entity, time, y, xs):
    p = df.set_index([entity, time])
    exog = sm.add_constant(p[xs])
    return PanelOLS(p[y], exog, entity_effects=True).fit(), RandomEffects(p[y], exog).fit()


def test_within_matches_linearmodels_on_grunfeld(panel):
    g = grunfeld()
    out = panel.within_estimator(g, "firm", "invest", ["value", "capital"])
    fe, _ = fe_re(g, "firm", "year", "invest", ["value", "capital"])
    assert list(out["params"].index) == ["value", "capital"]
    assert out["params"].to_numpy() == pytest.approx(fe.params[["value", "capital"]].to_numpy(), abs=1e-8)
    assert out["se"].to_numpy() == pytest.approx(fe.std_errors[["value", "capital"]].to_numpy(), abs=1e-8)
    assert out["df_resid"] == 220 - 11 - 2


def test_within_unbalanced_panel(panel):
    df = simulate(1)
    df = df.drop(index=np.random.default_rng(1).choice(len(df), 150, replace=False))
    out = panel.within_estimator(df, "entity", "y", ["x", "z"])
    fe, _ = fe_re(df, "entity", "time", "y", ["x", "z"])
    assert out["params"].to_numpy() == pytest.approx(fe.params[["x", "z"]].to_numpy(), abs=1e-8)
    assert out["se"].to_numpy() == pytest.approx(fe.std_errors[["x", "z"]].to_numpy(), abs=1e-8)


@pytest.mark.parametrize("seed", [2, 3, 4])
def test_within_removes_correlated_effect(panel, seed):
    df = simulate(seed)
    out = panel.within_estimator(df, "entity", "y", ["x", "z"])
    pooled = sm.OLS(df.y, sm.add_constant(df[["x", "z"]])).fit().params["x"]
    assert out["params"]["x"] == pytest.approx(0.5, abs=0.08)
    assert pooled > 0.5 + 0.25                      # pooled OLS bị omitted variable bias


def test_time_invariant_regressor_raises(panel):
    df = simulate(5)
    df["region"] = df.entity % 3                      # không đổi trong từng entity
    with pytest.raises(ValueError):
        panel.within_estimator(df, "entity", "y", ["x", "region"])


def test_hausman_grunfeld(panel):
    fe, re = fe_re(grunfeld(), "firm", "year", "invest", ["value", "capital"])
    h, p = panel.hausman(fe.params, re.params, fe.cov, re.cov)
    assert h == pytest.approx(3.97, abs=0.01)
    assert p == pytest.approx(0.138, abs=0.001)


@pytest.mark.parametrize("seed", [6, 7, 8])
def test_hausman_detects_correlated_effects(panel, seed):
    fe, re = fe_re(simulate(seed, rho=1.0), "entity", "time", "y", ["x", "z"])
    _, p_bad = panel.hausman(fe.params, re.params, fe.cov, re.cov)
    fe, re = fe_re(simulate(seed, rho=0.0), "entity", "time", "y", ["x", "z"])
    _, p_ok = panel.hausman(fe.params, re.params, fe.cov, re.cov)
    assert p_bad < 0.001
    assert p_ok > 0.01


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 300
