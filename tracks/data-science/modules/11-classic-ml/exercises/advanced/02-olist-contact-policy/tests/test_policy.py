import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)

COSTS = {"tp": 5.0, "fp": 5.0, "fn": 30.0, "tn": 0.0}


@pytest.fixture(scope="module")
def policy():
    return ex.module("policy.py")


def calibrated(seed: int, n: int = 6000):
    rng = np.random.default_rng(seed)
    p = rng.beta(1.0, 7.0, n)
    return (rng.random(n) < p).astype(int), p


def cost(y, p, t, costs=COSTS):
    y = np.asarray(y).astype(bool)
    pred = p >= t
    return (costs["tp"] * np.sum(y & pred) + costs["fp"] * np.sum(~y & pred)
            + costs["fn"] * np.sum(y & ~pred) + costs["tn"] * np.sum(~y & ~pred)) / len(y)


def brute_force(y, p, cap, costs=COSTS):
    grid = np.r_[np.unique(p), np.inf]
    ok = [t for t in grid if np.mean(p >= t) <= cap]
    return min(cost(y, p, t, costs) for t in ok)


def test_unconstrained_when_capacity_is_loose(policy):
    y, p = calibrated(0)
    t = policy.capacity_threshold(y, p, COSTS, max_contact_rate=1.0)
    assert cost(y, p, t) == pytest.approx(brute_force(y, p, 1.0))


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("cap", [0.03, 0.08])
def test_binding_capacity(policy, seed, cap):
    y, p = calibrated(seed)
    t = policy.capacity_threshold(y, p, COSTS, max_contact_rate=cap)
    assert np.mean(p >= t) <= cap + 1e-12
    assert cost(y, p, t) == pytest.approx(brute_force(y, p, cap))
    assert cost(y, p, t) >= brute_force(y, p, 1.0) - 1e-12


def test_zero_capacity_contacts_nobody(policy):
    y, p = calibrated(1)
    t = policy.capacity_threshold(y, p, COSTS, max_contact_rate=0.0)
    assert np.mean(p >= t) == 0


def test_bootstrap_saving(policy):
    y, p = calibrated(2)
    t = 0.2
    saving, lo, hi = policy.bootstrap_saving(y, p, t, COSTS, n_boot=500, seed=0)
    assert saving == pytest.approx(cost(y, p, np.inf) - cost(y, p, t))
    assert lo < saving < hi
    assert (lo, hi) == policy.bootstrap_saving(y, p, t, COSTS, n_boot=500, seed=0)[1:]
    # sai số chuẩn của trung bình: CI 95% rộng cỡ 2 × 1.96 × sd / sqrt(n)
    per_order = np.where(p >= t, np.where(y == 1, 30 - 5, -5), 0)
    expected_width = 2 * 1.96 * per_order.std() / np.sqrt(len(y))
    assert hi - lo == pytest.approx(expected_width, rel=0.2)


def test_bootstrap_ci_shrinks_with_more_data(policy):
    y, p = calibrated(3, n=20000)
    _, lo_small, hi_small = policy.bootstrap_saving(y[:2000], p[:2000], 0.2, COSTS, n_boot=400, seed=1)
    _, lo_big, hi_big = policy.bootstrap_saving(y, p, 0.2, COSTS, n_boot=400, seed=1)
    assert hi_big - lo_big < 0.5 * (hi_small - lo_small)


def test_decision_doc_written():
    doc = ex.read("DECISION.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 450
