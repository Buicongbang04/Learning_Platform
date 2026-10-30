import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.proportion import proportions_ztest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("ab_readout.ipynb")


def ab_fixture():
    # ad: 8 người, 2 chuyển đổi; psa: 4 người, 1 chuyển đổi
    return pd.DataFrame({
        "user_id": range(12),
        "group": ["ad"] * 8 + ["psa"] * 4,
        "converted": [True, True] + [False] * 6 + [True, False, False, False],
        "total_ads": [1] * 12,
        "most_ads_day": ["Monday", "Tuesday"] * 4 + ["Monday", "Monday", "Monday", "Tuesday"],
        "most_ads_hour": [10] * 12,
    })


def test_summarize(nb):
    df = ab_fixture()
    before = df.copy()
    out = nb.summarize(df)
    assert list(out.index) == ["ad", "psa"]
    assert out["users"].tolist() == [8, 4]
    assert out["conversions"].tolist() == [2, 1]
    assert out["rate"].tolist() == pytest.approx([0.25, 0.25])
    pd.testing.assert_frame_equal(df, before)


def test_srm_check(nb):
    ok = nb.srm_check({"ad": 960, "psa": 40}, {"ad": 0.96, "psa": 0.04})
    assert ok["chi2"] == pytest.approx(0.0)
    assert ok["p"] == pytest.approx(1.0)
    # 920/80 khi thiết kế 96/4: kỳ vọng 960/40 -> chi2 = 40²/960 + 40²/40
    bad = nb.srm_check(pd.Series({"psa": 80, "ad": 920}), {"ad": 0.96, "psa": 0.04})
    assert bad["chi2"] == pytest.approx(1600 / 960 + 1600 / 40)
    assert bad["p"] < 1e-9


def test_segment_balance(nb):
    df = ab_fixture()
    out = nb.segment_balance(df, "most_ads_day")
    # bảng [[Mon: ad 4, psa 3], [Tue: ad 4, psa 1]]
    from scipy.stats import chi2_contingency
    ref = chi2_contingency([[4, 3], [4, 1]], correction=False)
    assert out["chi2"] == pytest.approx(ref[0])
    assert out["p"] == pytest.approx(ref[1])
    assert out["dof"] == 1


def test_diff_ci_against_statsmodels(nb):
    out = nb.diff_ci(300, 10000, 250, 10000)
    assert out["rate_t"] == pytest.approx(0.03)
    assert out["diff"] == pytest.approx(0.005)
    se = np.sqrt(0.03 * 0.97 / 10000 + 0.025 * 0.975 / 10000)
    assert out["ci_low"] == pytest.approx(0.005 - 1.959964 * se, abs=1e-7)
    assert out["ci_high"] == pytest.approx(0.005 + 1.959964 * se, abs=1e-7)
    assert out["rel_lift"] == pytest.approx(0.2)
    _, p = proportions_ztest([300, 250], [10000, 10000])
    assert out["p"] == pytest.approx(p)


def test_diff_ci_alpha_and_sign(nb):
    narrow = nb.diff_ci(100, 1000, 120, 1000, alpha=0.10)
    wide = nb.diff_ci(100, 1000, 120, 1000, alpha=0.01)
    assert narrow["diff"] == pytest.approx(-0.02)
    assert wide["ci_low"] < narrow["ci_low"] and wide["ci_high"] > narrow["ci_high"]


@pytest.mark.parametrize("args, expected", [
    ((0.01, 0.03, 0.005, False, True), "investigate"),
    ((0.01, 0.03, 0.005, True, False), "do_not_ship"),
    ((0.001, 0.004, 0.005, True, True), "do_not_ship"),   # có ý nghĩa nhưng chắc chắn nhỏ hơn mde
    ((-0.002, 0.003, 0.005, True, True), "do_not_ship"),  # quanh 0, không thể đạt mde
    ((-0.03, -0.01, 0.005, True, True), "do_not_ship"),
    ((0.002, 0.012, 0.005, True, True), "ship"),
    ((-0.002, 0.012, 0.005, True, True), "inconclusive"),
])
def test_decide(nb, args, expected):
    assert nb.decide(*args) == expected


@pytest.fixture(scope="module")
def real_ab(nb):
    return nb.read_ab(ex.dataset("marketing-ab") / "marketing_AB.csv")


def test_real_readout(nb, real_ab):
    summary = nb.summarize(real_ab)
    assert summary["users"].tolist() == [564577, 23524]
    assert summary["conversions"].tolist() == [14423, 420]
    assert nb.srm_check(summary["users"], {"ad": 0.96, "psa": 0.04})["p"] > 0.99
    res = nb.diff_ci(14423, 564577, 420, 23524)
    assert res["diff"] == pytest.approx(0.0076925, abs=1e-6)
    assert res["ci_low"] == pytest.approx(0.0059509, abs=1e-6)
    assert res["rel_lift"] == pytest.approx(0.43085, abs=1e-4)
    assert res["p"] == pytest.approx(1.705e-13, rel=0.01)
    day = nb.segment_balance(real_ab, "most_ads_day")
    assert day["dof"] == 6
    assert day["chi2"] == pytest.approx(235.61, abs=0.01)
