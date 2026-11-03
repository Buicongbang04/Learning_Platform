import math
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)
PRICES = Path(__file__).resolve().parents[1] / "prices.yaml"
SPOT_A100 = {"market": "spot", "preemptions_per_hour": 0.02, "checkpoint_every_h": 2, "restart_h": 0.25}
PLANS = [
    {"name": "a100x8-od", "gpu": "a100-80gb", "n_gpus": 8, "single_gpu_hours": 800, "efficiency": 0.8},
    {"name": "a100x8-spot", "gpu": "a100-80gb", "n_gpus": 8, "single_gpu_hours": 800, "efficiency": 0.8, **SPOT_A100},
    {"name": "h100x8-od", "gpu": "h100-80gb", "n_gpus": 8, "single_gpu_hours": 300, "efficiency": 0.75},
    {"name": "h100x8-spot", "gpu": "h100-80gb", "n_gpus": 8, "single_gpu_hours": 300, "efficiency": 0.75,
     "market": "spot", "preemptions_per_hour": 0.05, "checkpoint_every_h": 1, "restart_h": 0.25},
    {"name": "t4x8-spot", "gpu": "t4-16gb", "n_gpus": 8, "single_gpu_hours": 50, "efficiency": 0.9, "market": "spot"},
    {"name": "l4x16-od", "gpu": "l4-24gb", "n_gpus": 16, "single_gpu_hours": 4000, "efficiency": 0.7},
]


@pytest.fixture(scope="module")
def mod():
    return ex.module("cost.py")


@pytest.fixture
def prices():
    return {"h100-80gb": {"on_demand": 6.98, "spot": 2.45}, "a100-80gb": {"on_demand": 4.10, "spot": 1.60},
            "l4-24gb": {"on_demand": 0.80, "spot": 0.32}, "t4-16gb": {"on_demand": 0.53, "spot": None}}


def write(tmp_path, text):
    path = tmp_path / "p.yaml"
    path.write_text(text)
    return path


def test_load_prices(mod, prices):
    assert mod.load_prices(PRICES) == prices
    loaded = mod.load_prices(PRICES)
    assert set(loaded) == {"h100-80gb", "a100-80gb", "l4-24gb", "t4-16gb"}
    assert loaded["t4-16gb"]["spot"] is None


@pytest.mark.parametrize("text", [
    "gpus: {}\n",
    "currency: USD\n",
    "gpus:\n  x: {on_demand: -1, spot: 1}\n",
    "gpus:\n  x: {on_demand: 0, spot: null}\n",
    "gpus:\n  x: {on_demand: '3.2', spot: null}\n",
    "gpus:\n  x: {on_demand: 2, spot: 0}\n",
    "gpus:\n  x: {spot: 1}\n",
])
def test_load_prices_rejects_bad_tables(mod, tmp_path, text):
    with pytest.raises(ValueError):
        mod.load_prices(write(tmp_path, text))


def test_scaling_efficiency(mod):
    assert mod.scaling_efficiency(1000, 7000, 8) == pytest.approx(0.875)
    assert mod.scaling_efficiency(500, 500, 1) == pytest.approx(1.0)


def test_wall_hours(mod):
    assert mod.wall_hours(800, 8, 0.8) == pytest.approx(125)
    assert mod.wall_hours(800, 1, 1.0) == pytest.approx(800)
    for bad in [(800, 0, 0.8), (800, 8, 0), (800, 8, 1.2)]:
        with pytest.raises(ValueError):
            mod.wall_hours(*bad)


def test_spot_overhead(mod):
    assert mod.spot_overhead_hours(125, 0.02, 2, 0.25) == pytest.approx(3.125)
    assert mod.spot_overhead_hours(125, 0.0, 2, 0.25) == 0


def test_on_demand_estimate(mod, prices):
    result = mod.estimate(prices, "a100-80gb", 8, 800, 0.8)
    assert result == pytest.approx({"wall_hours": 125, "gpu_hours": 1000, "cost": 4100})


def test_spot_estimate_pays_for_lost_work(mod, prices):
    result = mod.estimate(prices, "a100-80gb", 8, 800, 0.8, **SPOT_A100)
    assert result == pytest.approx({"wall_hours": 128.125, "gpu_hours": 1025, "cost": 1640})


def test_estimate_rejects_unavailable_choices(mod, prices):
    with pytest.raises(ValueError):
        mod.estimate(prices, "t4-16gb", 8, 50, 0.9, market="spot")
    with pytest.raises(ValueError):
        mod.estimate(prices, "b200", 8, 50, 0.9)
    with pytest.raises(ValueError):
        mod.estimate(prices, "a100-80gb", 8, 50, 0.9, market="reserved")


def test_cheapest_within_deadline(mod, prices):
    best = mod.cheapest(prices, PLANS, deadline_h=200)
    ok = (best is not None and best.get("name") == "h100x8-spot" and best.get("wall_hours") == pytest.approx(51.875)
          and best.get("cost") == pytest.approx(1016.75) and best.get("gpu_hours") == pytest.approx(415))
    assert ok, "Phương án được chọn hoặc số của nó chưa đúng với deadline 200 giờ"


def test_tight_deadline_forces_on_demand(mod, prices):
    best = mod.cheapest(prices, PLANS, deadline_h=51)
    ok = best is not None and best.get("name") == "h100x8-od" and best.get("cost") == pytest.approx(2792)
    assert ok, "Phương án được chọn hoặc số của nó chưa đúng với deadline 51 giờ"


def test_no_plan_meets_deadline(mod, prices):
    assert mod.cheapest(prices, PLANS, deadline_h=10) is None


def test_young_checkpoint_interval(mod):
    assert mod.optimal_checkpoint_every_h(0.05, 0.02) == pytest.approx(math.sqrt(5))
    assert mod.optimal_checkpoint_every_h(0.05, 0) == math.inf
