import pytest

from testkit import Exercise

ex = Exercise(__file__)
DATA = ex.dir / "data"


@pytest.fixture(scope="module")
def finops():
    return ex.module("finops.py")


def given(finops):
    return finops.load_usage(DATA / "usage-2026-10.csv"), finops.load_pricing(DATA / "pricing.yaml")


def find(rows, workload, env="prod"):
    return next(r for r in rows if r["workload"] == workload and r["env"] == env)


def test_load_usage(finops):
    rows, pricing = given(finops)
    assert len(rows) == 10 and pricing["orders"] == 412000
    api = find(rows, "olist-api")
    assert api["replicas"] == 6 and api["cpu_request_m"] == 1000 and isinstance(api["mem_max_mi"], int)
    assert find(rows, "loadtest-rig", "staging")["team"] is None
    assert find(rows, "olist-api", "staging")["team"] == "checkout"


def test_load_rejects_bad_files(finops, tmp_path):
    bad = tmp_path / "usage.csv"
    bad.write_text("workload,team,env,replicas\nx,a,prod,1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        finops.load_usage(bad)
    negative = tmp_path / "negative.csv"
    negative.write_text(",".join(finops.FIELDS) + "\nx,a,prod,-1,744,100,128,10,10\n", encoding="utf-8")
    with pytest.raises(ValueError):
        finops.load_usage(negative)
    pricing = tmp_path / "pricing.yaml"
    pricing.write_text("vcpu_hour: 0.034\ngib_hour: 0.0046\n", encoding="utf-8")
    with pytest.raises(ValueError):
        finops.load_pricing(pricing)


@pytest.mark.parametrize("workload,env,expected", [("olist-api", "prod", 192.84), ("search-indexer", "prod", 105.35),
                                                   ("etl-nightly", "prod", 13.0), ("loadtest-rig", "staging", 257.13)])
def test_cost_by_request(finops, workload, env, expected):
    rows, pricing = given(finops)
    assert finops.cost(find(rows, workload, env), pricing) == pytest.approx(expected, abs=0.01)


def test_cost_with_override(finops):
    rows, pricing = given(finops)
    assert finops.cost(find(rows, "olist-api"), pricing, 400, 960) == pytest.approx(6 * 744 * (0.4 * 0.034 + 960 / 1024 * 0.0046))


@pytest.mark.parametrize("workload,env,expected", [
    ("olist-api", "prod", {"cpu_m": 400, "mem_mi": 960, "action": "down"}),
    ("olist-worker", "prod", {"cpu_m": 550, "mem_mi": 1152, "action": "up"}),
    ("search-indexer", "prod", {"cpu_m": 1000, "mem_mi": 9536, "action": "up"}),
    ("grafana", "prod", {"cpu_m": 50, "mem_mi": 384, "action": "down"}),
    ("feature-preview-142", "staging", {"cpu_m": 50, "mem_mi": 192, "action": "down"}),
])
def test_rightsize(finops, workload, env, expected):
    rows, _ = given(finops)
    assert finops.rightsize(find(rows, workload, env)) == expected


def test_rightsize_floor_keep_and_headroom(finops):
    row = {"cpu_request_m": 50, "mem_request_mi": 128, "cpu_p95_m": 1, "mem_max_mi": 1}
    assert finops.rightsize(row) == {"cpu_m": 50, "mem_mi": 128, "action": "keep"}
    row = {"cpu_request_m": 300, "mem_request_mi": 256, "cpu_p95_m": 250, "mem_max_mi": 200}
    assert finops.rightsize(row) == {"cpu_m": 300, "mem_mi": 256, "action": "keep"}
    assert finops.rightsize(row, headroom=0.5) == {"cpu_m": 400, "mem_mi": 320, "action": "up"}


def test_allocate_shared_cost_by_share(finops):
    rows, pricing = given(finops)
    teams = finops.allocate(rows, pricing)
    assert teams == pytest.approx({"checkout": 393.4, "data": 418.58, "platform": 20.71, "search": 467.02, "unallocated": 393.4},
                                  abs=0.02)
    assert sum(teams.values()) == pytest.approx(1314.10 + 379.0, abs=0.05)


def test_savings_and_idle(finops):
    rows, pricing = given(finops)
    assert finops.savings(rows, pricing) == pytest.approx(892.76, abs=0.02)
    assert finops.idle(rows) == [("feature-preview-142", "staging"), ("loadtest-rig", "staging"), ("olist-api", "staging")]


def test_unit_cost(finops):
    rows, pricing = given(finops)
    assert finops.unit_cost(rows, pricing) == pytest.approx(4.1095, abs=1e-3)
