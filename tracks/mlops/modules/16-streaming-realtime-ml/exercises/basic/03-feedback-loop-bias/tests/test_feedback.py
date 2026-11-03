import random

import pytest

from testkit import Exercise

ex = Exercise(__file__)
ROUNDS = 4
PER_ROUND = 5_000


@pytest.fixture(scope="module")
def fb():
    return ex.module("feedback.py")


def simulate(epsilon, seed, start=0.9, step=0.15, rounds=ROUNDS, n=PER_ROUND):
    rng = random.Random(seed)
    log, truth, threshold = [], [], start
    for r in range(rounds):
        for _ in range(n):
            risk = rng.random()
            fraud = int(rng.random() < 0.02 + 0.3 * risk**2)
            blocked = risk >= threshold
            p_approve = epsilon if blocked else 1.0
            approved = (not blocked) or rng.random() < epsilon
            log.append({"round": r, "risk": risk, "approved": approved, "p_approve": p_approve, "label": fraud if approved else None})
            truth.append((r, fraud))
        threshold -= step
    return log, truth


def row(label, p=1.0, r=0):
    return {"round": r, "risk": 0.5, "approved": label is not None, "p_approve": p, "label": label}


def test_naive_rate_uses_labelled_rows(fb):
    log = [row(1), row(0), row(0), row(None, 0.5), row(1, 0.5)]
    assert fb.naive_rate(log) == pytest.approx(0.5)
    assert fb.naive_rate([row(None, 0.5)]) is None


def test_ipw_rate_weights_by_inverse_propensity(fb):
    log = [row(1), row(0), row(0), row(None, 0.5), row(1, 0.5)]
    assert fb.ipw_rate(log) == pytest.approx((1 + 1 / 0.5) / 5)
    assert fb.ipw_rate([row(0), row(None, 0.25), row(None, 0.25), row(None, 0.25), row(1, 0.25)]) == pytest.approx(4 / 5)
    assert fb.ipw_rate([row(1), row(None, 0.5), row(None, 0.5), row(0, 0.5)]) == pytest.approx(1 / 4)


def test_ipw_impossible_without_exploration(fb):
    assert fb.ipw_rate([row(1), row(None, 0.0)]) is None
    report = fb.bias_report([row(1), row(0), row(None, 0.0)])
    assert report["biased"] is None and report["ipw"] is None and report["naive"] == pytest.approx(0.5)


def test_closed_loop_bias_detected(fb):
    log, truth = simulate(0.1, seed=3)
    true_rate = sum(f for _, f in truth) / len(truth)
    report = fb.bias_report(log)
    assert report["ipw"] == pytest.approx(true_rate, abs=0.015)
    assert report["naive"] < true_rate - 0.03
    assert report["gap"] == pytest.approx(report["naive"] - report["ipw"])
    assert report["biased"] is True


def test_gap_grows_as_model_blocks_more(fb):
    log, truth = simulate(0.1, seed=4)
    rounds = fb.per_round(log)
    assert [r["round"] for r in rounds] == list(range(ROUNDS))
    naive = [r["naive"] for r in rounds]
    assert all(b < a for a, b in zip(naive, naive[1:]))
    assert rounds[-1]["gap"] < rounds[0]["gap"] - 0.03
    for r in rounds:
        actual = sum(f for k, f in truth if k == r["round"]) / PER_ROUND
        assert r["ipw"] == pytest.approx(actual, abs=0.03)
    assert all(r["biased"] for r in rounds[1:])


def test_no_bias_when_model_does_not_gate_labels(fb):
    log, _ = simulate(0.1, seed=5, start=1.5, step=0.0)
    report = fb.bias_report(log)
    assert report["gap"] == pytest.approx(0.0, abs=1e-12)
    assert report["biased"] is False
    assert all(r["biased"] is False for r in fb.per_round(log))


def test_tolerance_is_respected(fb):
    log = [row(1), row(0), row(None, 0.5), row(0, 0.5)]
    report = fb.bias_report(log, tolerance=0.5)
    assert report["gap"] == pytest.approx(1 / 3 - 1 / 4)
    assert report["biased"] is False
    assert fb.bias_report(log, tolerance=0.05)["biased"] is True
