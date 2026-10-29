import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("analysis.ipynb")


def make_df(n: int, p30: float, p40: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames = []
    for version, p in (("gate_30", p30), ("gate_40", p40)):
        r7 = rng.random(n) < p
        frames.append(pd.DataFrame({
            "userid": rng.integers(1, 10**7, n),
            "version": version,
            "sum_gamerounds": rng.poisson(50, n),
            "retention_1": r7 | (rng.random(n) < 0.3),   # ai quay lại ngày 7 thường cũng quay lại ngày 1
            "retention_7": r7,
        }))
    return pd.concat(frames, ignore_index=True)


SMALL = pd.DataFrame({
    "userid": [1, 2, 3, 4, 5, 6, 7],
    "version": ["gate_30", "gate_30", "gate_30", "gate_40", "gate_40", "gate_40", "gate_40"],
    "sum_gamerounds": [3, 40, 120, 0, 15, 60, 9],
    "retention_1": [False, True, True, False, True, True, False],
    "retention_7": [False, False, True, False, False, True, False],
})


def test_retention_summary_values(nb):
    out = nb.retention_summary(SMALL)
    assert list(out.index) == ["gate_30", "gate_40"]
    assert out.loc["gate_30", "n"] == 3 and out.loc["gate_40", "n"] == 4
    assert out.loc["gate_30", "retention_1"] == pytest.approx(2 / 3)
    assert out.loc["gate_40", "retention_7"] == pytest.approx(1 / 4)
    assert {"n", "retention_1", "retention_7"} <= set(out.columns)


def test_bootstrap_ci_detects_negative_effect(nb):
    df = make_df(20000, 0.20, 0.17, seed=1)
    diff, lo, hi = nb.bootstrap_diff_ci(df, "retention_7")
    observed = df[df.version == "gate_40"].retention_7.mean() - df[df.version == "gate_30"].retention_7.mean()
    assert diff == pytest.approx(observed)
    assert lo < diff < hi < 0
    assert hi - lo == pytest.approx(2 * 1.96 * np.sqrt(0.2 * 0.8 / 20000 + 0.17 * 0.83 / 20000), rel=0.15)


def test_bootstrap_is_reproducible_with_seed(nb):
    df = make_df(3000, 0.2, 0.2, seed=2)
    assert nb.bootstrap_diff_ci(df, "retention_1", n_boot=500, seed=7) == nb.bootstrap_diff_ci(df, "retention_1", n_boot=500, seed=7)


def test_wider_interval_for_smaller_alpha(nb):
    df = make_df(3000, 0.2, 0.2, seed=3)
    _, lo95, hi95 = nb.bootstrap_diff_ci(df, "retention_7", n_boot=1000)
    _, lo99, hi99 = nb.bootstrap_diff_ci(df, "retention_7", n_boot=1000, alpha=0.01)
    assert lo99 < lo95 and hi99 > hi95


def test_decision_three_branches(nb):
    assert nb.decision(make_df(20000, 0.20, 0.17, seed=4)) == "keep_gate_30"
    assert nb.decision(make_df(20000, 0.17, 0.20, seed=5)) == "ship_gate_40"
    same = make_df(2000, 0.2, 0.2, seed=6)
    same.loc[same.version == "gate_40", "retention_7"] = same.loc[same.version == "gate_30", "retention_7"].to_numpy()
    assert nb.decision(same) == "inconclusive"


def test_real_cookie_cats(nb):
    df = pd.read_csv(ex.dataset("cookie-cats") / "cookie_cats.csv")
    out = nb.retention_summary(df)
    assert out.loc["gate_30", "n"] == 44700 and out.loc["gate_40", "n"] == 45489
    assert out.loc["gate_30", "retention_7"] == pytest.approx(0.1902, abs=5e-4)
    assert out.loc["gate_40", "retention_7"] == pytest.approx(0.1820, abs=5e-4)
    assert nb.decision(df) == "keep_gate_30"
