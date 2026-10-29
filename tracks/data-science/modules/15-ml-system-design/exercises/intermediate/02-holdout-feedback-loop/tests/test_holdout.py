import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)

EFFECT = -0.10   # can thiệp giảm 10 điểm % xác suất review xấu


@pytest.fixture(scope="module")
def ho():
    return ex.module("holdout.py")


def simulate(seed: int, n: int = 30000, flag_share: float = 0.1, holdout_share: float = 0.2) -> pd.DataFrame:
    """Đơn rủi ro cao được cảnh báo; can thiệp có tác dụng thật EFFECT trên mọi đơn được can thiệp."""
    rng = np.random.default_rng(seed)
    risk = rng.beta(1.2, 8.0, n)
    score = np.log(risk / (1 - risk)) + rng.normal(0, 0.5, n)
    flagged = score >= np.quantile(score, 1 - flag_share)
    holdout = flagged & (rng.random(n) < holdout_share)
    treated = flagged & ~holdout
    p = np.clip(risk + EFFECT * treated, 0, 1)
    return pd.DataFrame({"risk": risk, "flagged": flagged, "holdout": holdout, "treated": treated,
                         "bad": (rng.random(n) < p).astype(int)})


SMALL = pd.DataFrame({
    "flagged": [True] * 6 + [False] * 4,
    "holdout": [True, True, False, False, False, False, False, False, False, False],
    "treated": [False, False, True, True, True, True, False, False, False, False],
    "bad":     [1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
})


def test_naive_by_hand(ho):
    # treated: 1/4; không treated: holdout 1/2 + không flagged 1/4 → 2/6
    assert ho.naive_effect(SMALL) == pytest.approx(1 / 4 - 2 / 6)


def test_holdout_by_hand(ho):
    diff, lo, hi = ho.holdout_effect(SMALL)
    assert diff == pytest.approx(1 / 4 - 1 / 2)
    se = np.sqrt(0.25 * 0.75 / 4 + 0.5 * 0.5 / 2)
    assert hi - lo == pytest.approx(2 * 1.959964 * se, rel=1e-4)
    assert lo < diff < hi


def test_realized_value_by_hand(ho):
    diff, lo, hi = ho.holdout_effect(SMALL)
    v, vlo, vhi = ho.realized_value(SMALL, cost_action=0.5, loss_event=30)
    assert v == pytest.approx(-diff * 30 - 0.5)
    assert vlo == pytest.approx(-hi * 30 - 0.5) and vhi == pytest.approx(-lo * 30 - 0.5)
    assert vlo < v < vhi


@pytest.mark.parametrize("seed", range(10))
def test_naive_is_misleading_but_holdout_recovers_effect(ho, seed):
    log = simulate(seed)
    assert ho.naive_effect(log) > 0            # nhìn như can thiệp có hại
    diff, lo, hi = ho.holdout_effect(log)
    se = (hi - lo) / (2 * 1.959964)
    assert abs(diff - EFFECT) < 3.5 * se       # gần tác động thật
    assert hi < 0                              # đủ mẫu để thấy có lợi


def test_ci_coverage_over_seeds(ho):
    covered = [lo <= EFFECT <= hi for lo, hi in (ho.holdout_effect(simulate(s, n=20000))[1:] for s in range(40))]
    assert np.mean(covered) >= 0.85


def test_retraining_rows_removes_feedback_bias(ho):
    log = simulate(0)
    rows = ho.retraining_rows(log, holdout_share=0.2)
    assert not rows.treated.any()
    assert len(rows) == (~log.treated).sum()
    assert set(rows.weight[~rows.holdout]) == {1.0}
    assert rows.weight[rows.holdout].iloc[0] == pytest.approx(5.0)
    # nhóm flagged sau khi đặt trọng số có cỡ xấp xỉ cỡ thật và tỉ lệ bad bằng rủi ro thật khi không can thiệp
    assert rows.weight[rows.flagged].sum() == pytest.approx(log.flagged.sum(), rel=0.1)
    true_untreated = log.risk[log.flagged].mean()
    assert rows.bad[rows.flagged].mean() == pytest.approx(true_untreated, abs=0.06)
    naive_flagged = log.bad[log.flagged].mean()          # dùng cả đơn đã can thiệp: rủi ro bị đánh giá thấp
    assert naive_flagged < true_untreated - 0.05
