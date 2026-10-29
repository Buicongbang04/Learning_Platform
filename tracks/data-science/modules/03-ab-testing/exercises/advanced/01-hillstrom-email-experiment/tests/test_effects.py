import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

ARMS = ["Mens E-Mail", "Womens E-Mail"]
METRICS = ["visit", "conversion", "spend"]
COLUMNS = ["arm", "metric", "diff", "ci_low", "ci_high", "p_value", "p_holm"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("analysis.ipynb")


def make_df(n: int = 6000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    lift = {"No E-Mail": 0.0, "Mens E-Mail": 0.06, "Womens E-Mail": 0.0}
    frames = []
    for arm, up in lift.items():
        visit = rng.random(n) < 0.10 + up
        conversion = visit & (rng.random(n) < 0.06)
        spend = np.where(conversion, rng.lognormal(4.5, 0.8, n), 0.0)
        frames.append(pd.DataFrame({
            "segment": arm, "visit": visit.astype(int), "conversion": conversion.astype(int), "spend": spend,
            "newbie": rng.integers(0, 2, n), "channel": rng.choice(["Web", "Phone", "Multichannel"], n),
        }))
    return pd.concat(frames, ignore_index=True)


def build(nb):
    # gọi trong test (không phải fixture) để starter chưa làm thì test FAIL chứ không ERROR
    return nb.effects_table(make_df())


def test_shape_and_columns(nb):
    table = build(nb)
    assert list(table.columns) == COLUMNS
    assert len(table) == 6
    assert set(zip(table.arm, table.metric)) == {(a, m) for a in ARMS for m in METRICS}


def test_diff_matches_means(nb):
    table = build(nb)
    df = make_df()
    row = table[(table.arm == "Mens E-Mail") & (table.metric == "visit")].iloc[0]
    expected = df[df.segment == "Mens E-Mail"].visit.mean() - df[df.segment == "No E-Mail"].visit.mean()
    assert row["diff"] == pytest.approx(expected)


def test_intervals_and_adjusted_pvalues(nb):
    table = build(nb)
    assert (table.ci_low <= table["diff"]).all() and (table["diff"] <= table.ci_high).all()
    assert (table.p_holm >= table.p_value - 1e-12).all()
    assert (table.p_holm <= 1).all()


def test_detects_real_effect_only(nb):
    table = build(nb)
    mens_visit = table[(table.arm == "Mens E-Mail") & (table.metric == "visit")].iloc[0]
    womens_visit = table[(table.arm == "Womens E-Mail") & (table.metric == "visit")].iloc[0]
    assert mens_visit.ci_low > 0 and mens_visit.p_holm < 0.05
    assert womens_visit.ci_low < 0 < womens_visit.ci_high


def test_custom_control(nb):
    df = make_df(seed=1)
    table = nb.effects_table(df, control="Womens E-Mail")
    assert set(table.arm) == {"Mens E-Mail", "No E-Mail"}


def test_real_hillstrom(nb):
    df = pd.read_csv(ex.dataset("hillstrom") / "hillstrom.csv")
    table = nb.effects_table(df)
    row = table[(table.arm == "Womens E-Mail") & (table.metric == "visit")].iloc[0]
    assert row["diff"] == pytest.approx(0.0452, abs=5e-4)
    assert row.ci_low > 0


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 250
