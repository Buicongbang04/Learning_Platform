import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

Y = [1, 0, 1, 0, 0, 1, 0, 0]
P = [0.9, 0.8, 0.7, 0.4, 0.4, 0.3, 0.2, 0.1]


@pytest.fixture(scope="module")
def value():
    return ex.module("value.py")


def calibrated(seed: int, n: int = 3000):
    rng = np.random.default_rng(seed)
    p = rng.beta(1.0, 8.0, n)
    return (rng.random(n) < p).astype(int), p


def brute(y, p, cost, loss, effect):
    y = np.asarray(y)
    best = 0.0
    for t in np.unique(p):
        sel = p >= t
        best = max(best, y[sel].sum() * (effect * loss - cost) - (sel.sum() - y[sel].sum()) * cost)
    return best


def test_confusion_counts_by_hand(value):
    assert value.confusion_counts(Y, P, 0.4) == {"tp": 2, "fp": 3, "fn": 1, "tn": 2}
    assert value.confusion_counts(Y, P, 0.95) == {"tp": 0, "fp": 0, "fn": 3, "tn": 5}
    out = value.confusion_counts(np.array(Y), np.array(P), 0.0)
    assert out == {"tp": 3, "fp": 5, "fn": 0, "tn": 0}


def test_expected_value_by_hand(value):
    # ngưỡng 0.7: chọn 3 đơn, 2 TP, 1 FP; TP = 0.15*30 - 0.5 = 4.0; FP = -0.5
    assert value.expected_value(Y, P, 0.7, 0.5, 30, 0.15) == pytest.approx(2 * 4.0 - 0.5)
    # gọi điện 5 R$: TP = 4.5 - 5 = -0.5
    assert value.expected_value(Y, P, 0.7, 5, 30, 0.15) == pytest.approx(2 * -0.5 - 5)
    assert value.expected_value(Y, P, np.inf, 5, 30, 0.15) == pytest.approx(0.0)


def test_break_even_precision(value):
    assert value.break_even_precision(0.5, 30, 0.15) == pytest.approx(1 / 9)
    assert value.break_even_precision(5, 30, 0.15) == pytest.approx(10 / 9)
    assert value.break_even_precision(1, 10, 1.0) == pytest.approx(0.1)


@pytest.mark.parametrize("seed", range(5))
def test_value_sign_matches_break_even(value, seed):
    y, p = calibrated(seed)
    pi_star = value.break_even_precision(0.5, 30, 0.15)
    for t in [0.05, 0.1, 0.2, 0.3, 0.4]:
        sel = p >= t
        if sel.sum() == 0:
            continue
        precision = y[sel].mean()
        if abs(precision - pi_star) < 1e-9:
            continue
        assert (value.expected_value(y, p, t, 0.5, 30, 0.15) > 0) == (precision > pi_star)


@pytest.mark.parametrize("seed", range(10))
def test_best_threshold_matches_brute_force(value, seed):
    y, p = calibrated(seed)
    t, v = value.best_threshold_value(y, p, 0.5, 30, 0.15)
    assert v == pytest.approx(brute(y, p, 0.5, 30, 0.15))
    assert value.expected_value(y, p, t, 0.5, 30, 0.15) == pytest.approx(v)
    assert v > 0


def test_never_profitable_chooses_no_action(value):
    y, p = calibrated(0)
    t, v = value.best_threshold_value(y, p, 5, 30, 0.15)
    assert t == np.inf
    assert v == pytest.approx(0.0)
