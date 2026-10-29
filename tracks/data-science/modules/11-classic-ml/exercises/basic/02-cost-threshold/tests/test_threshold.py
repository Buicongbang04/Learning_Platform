import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Olist: liên hệ chủ động tốn 5 R$; bỏ lỡ một đơn sẽ bị review xấu tốn 30 R$
COSTS = {"fp": 5.0, "fn": 30.0}


@pytest.fixture(scope="module")
def th():
    return ex.module("threshold.py")


def calibrated(seed: int, n: int = 8_000):
    """Xác suất đã calibrate: nhãn được rút đúng từ p."""
    rng = np.random.default_rng(seed)
    p = rng.beta(1.2, 6, n)
    y = (rng.random(n) < p).astype(int)
    return y, p


def test_expected_cost_by_hand(th):
    y = np.array([1, 1, 0, 0, 0])
    p = np.array([0.9, 0.2, 0.6, 0.1, 0.3])
    # ngưỡng 0.5: dự đoán dương ở 0.9 (TP), 0.6 (FP); bỏ lỡ 0.2 (FN)
    assert th.expected_cost(y, p, 0.5, COSTS) == pytest.approx((5 + 30) / 5)
    # p >= ngưỡng là dương: ngưỡng 0.2 bắt cả 0.2
    assert th.expected_cost(y, p, 0.2, COSTS) == pytest.approx((5 + 5) / 5)


def test_expected_cost_uses_all_four_cells(th):
    y = np.array([1, 0])
    p = np.array([0.8, 0.1])
    costs = {"tp": 5.0, "fp": 5.0, "fn": 30.0, "tn": 0.0}
    assert th.expected_cost(y, p, 0.5, costs) == pytest.approx(2.5)


def test_bayes_threshold(th):
    assert th.bayes_threshold(COSTS) == pytest.approx(5 / 35)
    assert th.bayes_threshold({"fp": 1, "fn": 1}) == pytest.approx(0.5)
    # liên hệ một đơn đúng cũng tốn 5: t* = (5 - 0) / ((5 - 0) + (30 - 5))
    assert th.bayes_threshold({"tp": 5, "fp": 5, "fn": 30, "tn": 0}) == pytest.approx(5 / 30)


def test_best_threshold_is_optimal_on_the_data(th):
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 300)
    p = np.clip(0.3 * y + rng.random(300) * 0.7, 0, 1)
    t = th.best_threshold(y, p, COSTS)
    grid = np.r_[np.unique(p), np.inf]
    best = min(th.expected_cost(y, p, g, COSTS) for g in grid)
    assert th.expected_cost(y, p, t, COSTS) == pytest.approx(best)


@pytest.mark.parametrize("seed", range(10))
def test_best_threshold_near_bayes_when_calibrated(th, seed):
    y, p = calibrated(seed)
    assert th.best_threshold(y, p, COSTS) == pytest.approx(5 / 35, abs=0.06)


def test_cost_driven_threshold_beats_half(th):
    y, p = calibrated(42)
    t = th.best_threshold(y, p, COSTS)
    assert th.expected_cost(y, p, t, COSTS) < 0.9 * th.expected_cost(y, p, 0.5, COSTS)


def test_contact_nobody_can_be_optimal(th):
    # liên hệ (đúng hay sai đều tốn 100) đắt hơn thiệt hại 1: tốt nhất là không liên hệ ai
    y, p = calibrated(3, n=5000)
    costs = {"tp": 100.0, "fp": 100.0, "fn": 1.0}
    t = th.best_threshold(y, p, costs)
    assert th.expected_cost(y, p, t, costs) == pytest.approx(y.mean() * 1.0)
    assert th.bayes_threshold(costs) > 1
