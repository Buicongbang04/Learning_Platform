import copy

import pytest

from testkit import Exercise

ex = Exercise(__file__)

CHAMPION = {
    "mae": 200.0,
    "latency_p95_ms": 40.0,
    "slices": {
        "airport": {"mae": 300.0, "n": 5000},
        "night": {"mae": 250.0, "n": 3000},
        "short": {"mae": 90.0, "n": 20000},
        "rare_zone": {"mae": 400.0, "n": 50},
    },
}


@pytest.fixture(scope="module")
def mod():
    return ex.module("promotion.py")


def challenger(mae=190.0, latency=42.0, **slice_mae):
    base = copy.deepcopy(CHAMPION)
    base["mae"] = mae
    base["latency_p95_ms"] = latency
    for name, value in slice_mae.items():
        base["slices"][name]["mae"] = value
    return base


def test_clear_win_promotes(mod):
    d = mod.decide_promotion(challenger(), CHAMPION)
    assert d.promote is True
    assert d.checks == {"overall_mae": True, "slices": True, "latency": True}
    assert len(d.reasons) == 1


def test_better_overall_but_worse_slice_is_rejected(mod):
    d = mod.decide_promotion(challenger(mae=180.0, airport=360.0), CHAMPION)
    assert d.promote is False
    assert d.checks == {"overall_mae": True, "slices": False, "latency": True}
    assert any("airport" in r for r in d.reasons)


def test_slice_within_tolerance_is_fine(mod):
    d = mod.decide_promotion(challenger(airport=300.0 * 1.04), CHAMPION)
    assert d.promote is True


def test_slice_exactly_at_tolerance_is_allowed(mod):
    d = mod.decide_promotion(challenger(airport=315.0), CHAMPION)
    assert d.checks["slices"] is True


def test_tiny_slice_is_ignored(mod):
    d = mod.decide_promotion(challenger(rare_zone=800.0), CHAMPION)
    assert d.promote is True


def test_min_slice_n_comes_from_policy(mod):
    d = mod.decide_promotion(challenger(rare_zone=800.0), CHAMPION, {"min_slice_n": 10})
    assert d.promote is False
    assert any("rare_zone" in r for r in d.reasons)


def test_missing_slice_cannot_be_verified(mod):
    c = challenger()
    del c["slices"]["night"]
    d = mod.decide_promotion(c, CHAMPION)
    assert d.promote is False
    assert any("night" in r for r in d.reasons)


def test_improvement_below_threshold_is_rejected(mod):
    d = mod.decide_promotion(challenger(mae=199.0), CHAMPION)
    assert d.promote is False
    assert d.checks["overall_mae"] is False


def test_improvement_exactly_at_threshold_promotes(mod):
    d = mod.decide_promotion(challenger(mae=198.0), CHAMPION)
    assert d.checks["overall_mae"] is True


def test_latency_ratio_boundary(mod):
    assert mod.decide_promotion(challenger(latency=48.0), CHAMPION).promote is True
    d = mod.decide_promotion(challenger(latency=48.5), CHAMPION)
    assert d.promote is False and d.checks["latency"] is False


def test_absolute_latency_ceiling(mod):
    d = mod.decide_promotion(challenger(latency=42.0), CHAMPION, {"max_latency_ms": 41.0})
    assert d.promote is False
    assert d.checks["latency"] is False


def test_multiple_failures_are_all_reported(mod):
    d = mod.decide_promotion(challenger(mae=199.5, latency=100.0, night=400.0), CHAMPION)
    assert d.promote is False
    assert d.checks == {"overall_mae": False, "slices": False, "latency": False}
    assert len(d.reasons) == 3


def test_nan_metric_never_promotes(mod):
    d = mod.decide_promotion(challenger(mae=float("nan")), CHAMPION)
    assert d.promote is False


def test_missing_latency_never_promotes(mod):
    c = challenger()
    del c["latency_p95_ms"]
    assert mod.decide_promotion(c, CHAMPION).promote is False


def test_no_champion_uses_absolute_limits(mod):
    assert mod.decide_promotion(challenger(), None).promote is True
    d = mod.decide_promotion(challenger(), None, {"max_mae": 150.0})
    assert d.promote is False and d.checks["overall_mae"] is False


def test_inputs_are_not_mutated(mod):
    c, policy = challenger(), {"min_improvement": 0.02}
    before = (copy.deepcopy(c), copy.deepcopy(CHAMPION), copy.deepcopy(policy))
    mod.decide_promotion(c, CHAMPION, policy)
    assert (c, CHAMPION, policy) == before
