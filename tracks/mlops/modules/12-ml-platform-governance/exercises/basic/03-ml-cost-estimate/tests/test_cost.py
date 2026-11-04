import copy
from pathlib import Path

import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)
FIXTURE = Path(__file__).parent / "fixtures" / "prices.yaml"

BASE = {
    "train": {"instance": "gpu.g5.xlarge", "hours_per_run": 3, "runs_per_month": 8, "spot": True},
    "serve": {"instance": "cpu.m5.xlarge", "replicas": 2, "utilization": 0.15, "scale_to_zero": False, "committed": False},
    "storage_gb": 500,
    "egress_gb": 200,
}


@pytest.fixture
def cost():
    return ex.module("cost.py")


@pytest.fixture
def prices():
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def test_price_table_is_unchanged(prices):
    assert yaml.safe_load(ex.path("prices.yaml").read_text(encoding="utf-8")) == prices


def test_base_scenario_numbers(cost, prices):
    assert cost.estimate(BASE, prices) == {
        "train": 8.48,
        "serve": 335.8,
        "idle_serve": 285.43,
        "storage": 11.5,
        "egress": 18.0,
        "total": 373.78,
    }


def test_spot_off_uses_full_train_price(cost, prices):
    scenario = copy.deepcopy(BASE)
    scenario["train"]["spot"] = False
    assert cost.estimate(scenario, prices)["train"] == 24.24


def test_scale_to_zero_bills_only_busy_hours_and_has_no_idle(cost, prices):
    scenario = copy.deepcopy(BASE)
    scenario["serve"]["scale_to_zero"] = True
    est = cost.estimate(scenario, prices)
    assert est["serve"] == 50.37
    assert est["idle_serve"] == 0.0
    assert est["total"] == 88.35


def test_committed_discount(cost, prices):
    scenario = copy.deepcopy(BASE)
    scenario["serve"]["committed"] = True
    est = cost.estimate(scenario, prices)
    assert est["serve"] == 208.2
    assert est["idle_serve"] == 176.97


def test_gpu_serving_dominates_the_bill(cost, prices):
    scenario = copy.deepcopy(BASE)
    scenario["serve"] = {"instance": "gpu.a100", "replicas": 1, "utilization": 0.4, "scale_to_zero": False}
    est = cost.estimate(scenario, prices)
    assert est["serve"] == 2993.0
    assert est["idle_serve"] == 1795.8
    assert est["total"] == 3030.98


def test_total_is_rounded_once_from_raw_parts(cost, prices):
    scenario = copy.deepcopy(BASE)
    scenario["train"].update({"hours_per_run": 1, "runs_per_month": 3})
    scenario["serve"].update({"replicas": 1, "utilization": 0.333, "scale_to_zero": True})
    scenario["storage_gb"] = 7
    scenario["egress_gb"] = 1
    est = cost.estimate(scenario, prices)
    raw = 1.01 * 3 * 0.35 + 0.23 * 730 * 0.333 + 7 * 0.023 + 0.09
    assert est["total"] == round(raw, 2)


def test_idle_share(cost, prices):
    assert cost.idle_share(cost.estimate(BASE, prices)) == 0.7636
    assert cost.idle_share({"idle_serve": 0.0, "total": 0.0}) == 0.0


def test_savings_applies_overrides_to_a_copy(cost, prices):
    snapshot = copy.deepcopy(BASE)
    result = cost.savings(BASE, prices, serve={"scale_to_zero": True})
    assert result == {"before": 373.78, "after": 88.35, "saved": 285.43}
    assert BASE == snapshot


def test_savings_partial_serve_override_keeps_other_keys(cost, prices):
    result = cost.savings(BASE, prices, serve={"replicas": 1}, storage_gb=100)
    assert result["after"] == round(8.484 + 167.9 + 2.3 + 18, 2)
    assert result["saved"] == round(373.78 - result["after"], 2)


def test_prices_are_not_mutated(cost, prices):
    snapshot = copy.deepcopy(prices)
    cost.estimate(BASE, prices)
    assert prices == snapshot


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda s: s["train"].update(instance="gpu.h100"), "gpu.h100"),
        (lambda s: s["serve"].update(instance="cpu.zzz"), "cpu.zzz"),
        (lambda s: s["serve"].update(utilization=1.2), "utilization"),
        (lambda s: s["serve"].update(utilization=-0.1), "utilization"),
        (lambda s: s["serve"].update(replicas=-1), "replicas"),
        (lambda s: s["train"].update(runs_per_month=-2), "runs_per_month"),
    ],
)
def test_invalid_input_raises_value_error(cost, prices, mutate, match):
    scenario = copy.deepcopy(BASE)
    mutate(scenario)
    with pytest.raises(ValueError, match=match):
        cost.estimate(scenario, prices)
