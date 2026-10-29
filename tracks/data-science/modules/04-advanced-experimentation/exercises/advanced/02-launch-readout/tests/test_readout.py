import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("readout.ipynb")


def make_log(n_users: int, novelty: float, seed: int, hte: float = 0.0, n_days: int = 21) -> pd.DataFrame:
    """User-ngày. Tác động = novelty · exp(−ngày phơi nhiễm / 3) + 1.0, cộng hte cho segment "b"."""
    rng = np.random.default_rng(seed)
    treat = (rng.random(n_users) < 0.5).astype(int)
    segment = np.where(rng.random(n_users) < 0.5, "a", "b")
    platform = np.where(rng.random(n_users) < 0.5, "android", "ios")
    first_day = rng.integers(0, 5, n_users)
    base = rng.normal(20, 5, n_users)
    frames = []
    for d in range(n_days):
        on = (first_day <= d) & (rng.random(n_users) < 0.6)
        idx = np.flatnonzero(on)
        exposure = d - first_day[idx]
        effect = (novelty * np.exp(-exposure / 3) + 1.0 + hte * (segment[idx] == "b")) * treat[idx]
        frames.append(pd.DataFrame({
            "user_id": idx, "treat": treat[idx], "segment": segment[idx], "platform": platform[idx],
            "first_day": first_day[idx], "day": d, "minutes": base[idx] + effect + rng.normal(0, 4, len(idx)),
        }))
    return pd.concat(frames, ignore_index=True)


SMALL = pd.DataFrame({
    "user_id": [1, 1, 2, 2, 3, 4, 4, 5],
    "treat": [1, 1, 1, 1, 0, 0, 0, 0],
    "segment": ["a", "a", "b", "b", "a", "b", "b", "a"],
    "platform": ["ios"] * 8,
    "first_day": [0, 0, 1, 1, 0, 2, 2, 0],
    "day": [0, 1, 1, 3, 0, 2, 3, 1],
    "minutes": [10.0, 8, 12, 6, 5, 7, 3, 4],
})


def test_effect_by_exposure_day_hand_example(nb):
    out = nb.effect_by_exposure_day(SMALL)
    # ngày phơi nhiễm 0: treat {10 (u1), 12 (u2)} vs control {5 (u3), 7 (u4)}
    assert out.loc[0, "diff"] == pytest.approx(11 - 6)
    assert out.loc[0, "n_t"] == 2 and out.loc[0, "n_c"] == 2
    assert out.loc[0, "se"] == pytest.approx(np.sqrt(np.var([10, 12], ddof=1) / 2 + np.var([5, 7], ddof=1) / 2))
    # ngày phơi nhiễm 1: treat {8 (u1)} vs control {3 (u4), 4 (u5)}
    assert out.loc[1, "diff"] == pytest.approx(8 - 3.5)
    assert {"diff", "se", "n_t", "n_c"} <= set(out.columns)


def test_novelty_slope_weighted(nb):
    effects = pd.DataFrame({"diff": [5.0, 4.0, 3.0, 2.0], "se": [0.5, 0.5, 0.5, 0.5]},
                           index=pd.Index([0, 1, 2, 3], name="exposure_day"))
    out = nb.novelty_slope(effects)
    assert out["slope"] == pytest.approx(-1.0)
    assert out["se"] == pytest.approx(0.5 / np.sqrt(5.0))      # sqrt(1 / sum w (x − x̄)²), w = 1/se²
    assert out["p_value"] < 1e-3
    # điểm có se lớn gần như không được tính
    noisy = effects.copy()
    noisy.loc[3] = [100.0, 1000.0]
    assert nb.novelty_slope(noisy)["slope"] == pytest.approx(-1.0, abs=0.01)
    assert nb.novelty_slope(effects, max_day=2)["slope"] == pytest.approx(-1.0)


def test_user_level(nb):
    users = nb.user_level(SMALL)
    assert users.loc[1, "minutes"] == pytest.approx(9.0)
    assert users.loc[4, "minutes"] == pytest.approx(5.0)
    assert users.loc[2, "treat"] == 1 and users.loc[2, "segment"] == "b"
    assert len(users) == 5


def test_detects_novelty(nb):
    log = make_log(6000, novelty=4.0, seed=1)
    effects = nb.effect_by_exposure_day(log)
    out = nb.novelty_slope(effects, max_day=14)
    assert out["slope"] < 0 and out["p_value"] < 0.001
    assert effects.loc[0, "diff"] > effects.loc[14, "diff"] + 1.5


def test_no_false_novelty(nb):
    zs = []
    for seed in range(3):
        effects = nb.effect_by_exposure_day(make_log(4000, novelty=0.0, seed=10 + seed))
        out = nb.novelty_slope(effects, max_day=14)
        zs.append(out["slope"] / out["se"])
    assert max(abs(z) for z in zs) < 3.5


def test_interaction_test(nb):
    users = nb.user_level(make_log(6000, novelty=0.0, seed=2, hte=2.0))
    seg = nb.interaction_test(users, "segment")
    assert seg["p_value"] < 1e-4
    assert seg["effects"].loc["b", "diff"] - seg["effects"].loc["a", "diff"] == pytest.approx(2.0, abs=1.1)
    plat = nb.interaction_test(users, "platform")
    assert plat["p_value"] > 0.001
    assert set(plat["effects"].index) == {"android", "ios"}


def test_report_written():
    report = ex.read("REPORT.md")
    assert "TODO" not in report
    assert len(report.split()) >= 300
