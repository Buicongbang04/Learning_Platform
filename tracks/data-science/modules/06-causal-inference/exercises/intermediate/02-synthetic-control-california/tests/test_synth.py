import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

PRE = list(range(1990, 2005))
POST = list(range(2005, 2013))


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("synth.ipynb")


def simulate(seed: int = 0, effect: float = -10.0) -> pd.DataFrame:
    """15 donor theo mô hình nhân tố; 'treated' = 0.5·d0 + 0.3·d1 + 0.2·d2 cộng nhiễu, tác động từ 2005."""
    rng = np.random.default_rng(seed)
    years = PRE + POST
    f1 = np.cumsum(rng.normal(0, 1, len(years)))
    f2 = np.linspace(0, 1, len(years))
    donors = {f"d{j}": 50 + rng.normal(0, 5) + rng.normal(1, 0.5) * f1 + rng.normal(0, 20) * f2
              + rng.normal(0, 0.3, len(years)) for j in range(15)}
    panel = pd.DataFrame(donors, index=years)
    treated = 0.5 * panel.d0 + 0.3 * panel.d1 + 0.2 * panel.d2 + rng.normal(0, 0.3, len(years))
    panel["treated"] = treated + np.where(np.array(years) >= 2005, effect, 0.0)
    return panel


def test_to_panel(nb):
    long = pd.DataFrame({"state": ["A", "A", "B", "B"], "year": [2001, 2000, 2000, 2001],
                         "cigsale": [2.0, 1.0, 3.0, 4.0]})
    panel = nb.to_panel(long)
    assert list(panel.index) == [2000, 2001]
    assert panel.loc[2001, "A"] == 2.0 and panel.loc[2000, "B"] == 3.0


def test_weights_exact_convex_combination(nb):
    donors = pd.DataFrame({"a": [1.0, 2, 3, 4], "b": [4.0, 3, 2, 1], "c": [0.0, 5, 0, 5]})
    y = 0.25 * donors.a + 0.75 * donors.b
    w = nb.synth_weights(y, donors)
    assert list(w.index) == ["a", "b", "c"]
    assert w.to_numpy() == pytest.approx([0.25, 0.75, 0.0], abs=1e-4)


def test_weights_outside_hull_stay_feasible(nb):
    donors = pd.DataFrame({"a": [1.0, 1, 1], "b": [2.0, 2, 2]})
    w = nb.synth_weights(pd.Series([5.0, 5, 5]), donors)    # không tổ hợp lồi nào đạt 5: dồn hết vào b
    assert (w >= -1e-9).all() and w.sum() == pytest.approx(1.0, abs=1e-6)
    assert w["b"] == pytest.approx(1.0, abs=1e-4)


@pytest.mark.parametrize("seed", range(5))
def test_recovers_effect_on_simulated_panel(nb, seed):
    panel = simulate(seed)
    w = nb.synth_weights(panel.loc[PRE, "treated"], panel.drop(columns="treated").loc[PRE])
    assert (w >= -1e-9).all() and w.sum() == pytest.approx(1.0, abs=1e-6)
    gap = nb.synth_gap(panel, "treated", PRE)
    assert nb.rmspe(gap, PRE) < 1.0
    assert gap.loc[POST].mean() == pytest.approx(-10.0, abs=1.5)


def test_rmspe(nb):
    gap = pd.Series([3.0, -4.0, 100.0], index=[1, 2, 3])
    assert nb.rmspe(gap, [1, 2]) == pytest.approx(np.sqrt(12.5))


def test_placebo_ranks_treated_first_in_simulation(nb):
    ratios = nb.placebo_ratios(simulate(0), "treated", PRE, POST)
    assert len(ratios) == 16
    assert ratios.index[0] == "treated"
    assert ratios.is_monotonic_decreasing


def test_real_california(nb):
    df = pd.read_csv(ex.dataset("prop99") / "smoking_data.csv")
    df["year"] = df["year"].astype(int)
    panel = nb.to_panel(df)
    pre, post = list(range(1970, 1989)), list(range(1989, 2001))
    w = nb.synth_weights(panel.loc[pre, "California"], panel.drop(columns="California").loc[pre])
    assert w.idxmax() == "Utah" and w.max() == pytest.approx(0.39, abs=0.03)
    gap = nb.synth_gap(panel, "California", pre)
    assert nb.rmspe(gap, pre) == pytest.approx(1.66, abs=0.05)
    assert gap.loc[2000] == pytest.approx(-26.6, abs=1.0)
    assert gap.loc[post].mean() == pytest.approx(-19.5, abs=1.0)
    ratios = nb.placebo_ratios(panel, "California", pre, post)
    assert len(ratios) == 39
    assert list(ratios.index).index("California") + 1 == 3
