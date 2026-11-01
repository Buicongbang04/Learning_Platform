import math

import numpy as np
import pytest
from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def ag():
    return ex.module("agreement.py")


# ---------- Cohen's kappa ----------

def test_kappa_hand_example(ag):
    a = ["y"] * 20 + ["y"] * 5 + ["n"] * 10 + ["n"] * 15
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    assert ag.cohen_kappa(a, b) == pytest.approx((0.7 - 0.5) / (1 - 0.5))


def test_kappa_matches_sklearn_multiclass(ag):
    from sklearn.metrics import cohen_kappa_score

    rng = np.random.default_rng(0)
    for _ in range(20):
        a = list(rng.choice(["neg", "neu", "pos"], size=60, p=[0.5, 0.1, 0.4]))
        b = [x if rng.random() < 0.7 else str(rng.choice(["neg", "neu", "pos"])) for x in a]
        assert ag.cohen_kappa(a, b) == pytest.approx(cohen_kappa_score(a, b))


def test_kappa_chance_and_perfect(ag):
    assert ag.cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == pytest.approx(1.0)
    assert ag.cohen_kappa([1, 1, 0, 0], [1, 0, 1, 0]) == pytest.approx(0.0)
    assert ag.cohen_kappa([True] * 9 + [False], [True] * 10) == pytest.approx(0.0), "90% khớp nhưng không hơn may rủi"
    assert math.isnan(ag.cohen_kappa(["x"] * 5, ["x"] * 5))
    with pytest.raises(ValueError):
        ag.cohen_kappa([1, 0], [1])


# ---------- calibration_report ----------

def test_calibration_report(ag):
    human = [True, True, True, True, False, False, False, False, True, False]
    judge = [True, True, True, False, True, False, False, False, None, None]
    r = ag.calibration_report(judge, human)
    assert r["n"] == 8 and r["unparsed"] == 2, "verdict None bị loại khỏi mọi tỉ lệ và được đếm riêng"
    assert r["accuracy"] == pytest.approx(6 / 8)
    assert r["false_pass"] == pytest.approx(1 / 4), "judge cho qua câu người chấm là sai"
    assert r["false_fail"] == pytest.approx(1 / 4)
    assert r["judge_pass_rate"] == pytest.approx(4 / 8) and r["human_pass_rate"] == pytest.approx(4 / 8)
    assert r["kappa"] == pytest.approx(0.5)


def test_calibration_report_one_class(ag):
    r = ag.calibration_report([True, False], [True, True])
    assert math.isnan(r["false_pass"]) and r["false_fail"] == pytest.approx(0.5)
    with pytest.raises(ValueError):
        ag.calibration_report([None, None], [True, False])


# ---------- position swap ----------

@pytest.mark.parametrize("v_ab, v_ba, expected", [
    ("first", "second", "A"),
    ("second", "first", "B"),
    ("tie", "tie", "tie"),
    ("first", "first", "inconsistent"),
    ("second", "second", "inconsistent"),
    ("first", "tie", "inconsistent"),
    ("tie", "first", "inconsistent"),
])
def test_resolve_swap(ag, v_ab, v_ba, expected):
    assert ag.resolve_swap(v_ab, v_ba) == expected


def test_resolve_swap_rejects_unknown(ag):
    with pytest.raises(ValueError):
        ag.resolve_swap("A", "second")
    with pytest.raises(ValueError):
        ag.resolve_swap("first", None)


def test_pairwise_summary(ag):
    pairs = [("first", "second")] * 5 + [("second", "first")] * 2 + [("first", "first")] * 2 + [("tie", "tie")]
    s = ag.pairwise_summary(pairs)
    assert (s["n"], s["A"], s["B"], s["tie"], s["inconsistent"]) == (10, 5, 2, 1, 2)
    assert s["consistency"] == pytest.approx(0.8)
    assert s["win_rate_A"] == pytest.approx((5 + 0.5 * 3) / 10), "tie và inconsistent tính nửa trận"
    assert s["first_rate"] == pytest.approx(11 / 18), "18 verdict quyết định, 11 chọn vị trí đầu"


def test_pairwise_summary_detects_pure_position_bias(ag):
    s = ag.pairwise_summary([("first", "first")] * 30)
    assert s["consistency"] == 0.0 and s["first_rate"] == 1.0 and s["win_rate_A"] == pytest.approx(0.5)
    s = ag.pairwise_summary([("tie", "tie")] * 3)
    assert math.isnan(s["first_rate"])
    with pytest.raises(ValueError):
        ag.pairwise_summary([])
