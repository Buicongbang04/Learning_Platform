import math

import pytest

from testkit import Exercise

ex = Exercise(__file__)
CACHE = {"qps": 2000, "cache_ms": 2, "cache_p99_ms": 5, "model_ms": 40, "model_p99_ms": 180, "model_cost_per_1k": 0.02,
         "cache_cost_per_hour": 1.5}
OPTIONS = [
    {"name": "teacher-realtime", "cost_per_day": 1000, "p99_ms": 250, "quality_drop": 0.0},
    {"name": "student-realtime", "cost_per_day": 100, "p99_ms": 60, "quality_drop": 0.02},
    {"name": "cache-teacher", "cost_per_day": 300, "p99_ms": 260, "quality_drop": 0.0},
    {"name": "batch-nightly", "cost_per_day": 40, "p99_ms": 8, "quality_drop": 0.06},
]


@pytest.fixture(scope="module")
def mod():
    return ex.module("tradeoffs.py")


def test_cache_with_moderate_hit_rate(mod):
    plan = mod.cache_plan(hit_rate=0.8, **CACHE)
    assert plan["mean_ms"] == pytest.approx(10.0)
    assert plan["p99_ms"] == pytest.approx(182.0)
    assert plan["model_calls_per_hour"] == pytest.approx(1_440_000)
    assert plan["cost_per_hour"] == pytest.approx(30.3)


def test_cache_tail_only_improves_when_misses_are_rare(mod):
    assert mod.cache_plan(hit_rate=0.98, **CACHE)["p99_ms"] == pytest.approx(182.0)
    high = mod.cache_plan(hit_rate=0.995, **CACHE)
    assert high["p99_ms"] == pytest.approx(5.0)
    assert high["mean_ms"] == pytest.approx(2.2)
    assert high["cost_per_hour"] == pytest.approx(2.22)


def test_cache_without_hits_costs_more_than_no_cache(mod):
    plan = mod.cache_plan(hit_rate=0.0, **CACHE)
    assert plan["mean_ms"] == pytest.approx(42.0)
    assert plan["cost_per_hour"] == pytest.approx(2000 * 3.6 * 0.02 + 1.5)


def test_cache_rejects_invalid_hit_rate(mod):
    with pytest.raises(ValueError):
        mod.cache_plan(hit_rate=1.2, **CACHE)
    with pytest.raises(ValueError):
        mod.cache_plan(hit_rate=-0.1, **CACHE)


def test_batch_is_cheaper_for_few_entities(mod):
    result = mod.batch_vs_realtime(2_000_000, 4, 0.01, 5_000_000, 0.03, 96)
    assert result["batch_cost_per_day"] == pytest.approx(80)
    assert result["realtime_cost_per_day"] == pytest.approx(246)
    assert result["batch_max_staleness_h"] == pytest.approx(6)
    assert result["cheaper"] == "batch"


def test_realtime_is_cheaper_for_huge_catalogue(mod):
    result = mod.batch_vs_realtime(50_000_000, 24, 0.01, 5_000_000, 0.03, 96)
    assert result["batch_cost_per_day"] == pytest.approx(12_000)
    assert result["batch_max_staleness_h"] == pytest.approx(1)
    assert result["cheaper"] == "realtime"


def test_batch_wins_a_tie(mod):
    result = mod.batch_vs_realtime(1_000_000, 1, 0.1, 1_000_000, 0.1, 0)
    assert result["cheaper"] == "batch"


def test_batch_rejects_zero_refreshes(mod):
    with pytest.raises(ValueError):
        mod.batch_vs_realtime(1000, 0, 0.01, 1000, 0.01, 0)


def test_distillation_breakeven(mod):
    assert mod.distillation_breakeven_days(0.5, 0.05, 9000, 2_000_000) == pytest.approx(10.0)
    assert mod.distillation_breakeven_days(0.5, 0.5, 9000, 2_000_000) == math.inf
    assert mod.distillation_breakeven_days(0.1, 0.2, 9000, 2_000_000) == math.inf


def test_choose_cheapest_option_that_meets_constraints(mod):
    assert mod.choose(OPTIONS, max_p99_ms=200, max_quality_drop=0.03) == "student-realtime"
    assert mod.choose(OPTIONS, max_p99_ms=300, max_quality_drop=0.0) == "cache-teacher"
    assert mod.choose(OPTIONS, max_p99_ms=300, max_quality_drop=0.1) == "batch-nightly"
    assert mod.choose(OPTIONS, max_p99_ms=5, max_quality_drop=0.1) is None


def test_choose_breaks_cost_ties_by_latency(mod):
    tied = [{"name": "a", "cost_per_day": 10, "p99_ms": 90, "quality_drop": 0.0},
            {"name": "b", "cost_per_day": 10, "p99_ms": 40, "quality_drop": 0.0}]
    assert mod.choose(tied, max_p99_ms=100, max_quality_drop=0.0) == "b"
    assert mod.choose(tied, max_p99_ms=60, max_quality_drop=0.0) == "b"
    assert mod.choose([], max_p99_ms=100, max_quality_drop=0.0) is None
