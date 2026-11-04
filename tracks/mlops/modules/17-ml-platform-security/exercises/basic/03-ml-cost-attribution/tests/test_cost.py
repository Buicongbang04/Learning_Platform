import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
PRICES = {"cpu_hour": 0.031, "gpu_hour": 0.90, "mem_gb_hour": 0.004}
NAMESPACES = {"eta-prod": "eta", "eta-train": "eta", "pricing": "pricing", "fraud-rt": "fraud", "search": "search", "ads": "ads"}
COST_CENTERS = {"eta": "CC-1001", "pricing": "CC-2041", "fraud": "CC-3307", "search": "CC-4410", "ads": "CC-5120"}
MODELS = {
    "eta-prod": ["eta-duration", "eta-surge"],
    "eta-train": ["eta-duration", ""],
    "pricing": ["pricing-tip-amount"],
    "fraud-rt": ["fraud-card", "fraud-account"],
    "search": ["search-ranker"],
    "ads": ["ads-ctr"],
    "tmp-notebooks": ["", "scratch"],
}
WORKLOAD = {"eta-train": "train", "tmp-notebooks": "notebook"}
COLUMNS = ["cpu_hours", "gpu_hours", "mem_gb_hours"]
PRICE_OF = {"cpu_hours": "cpu_hour", "gpu_hours": "gpu_hour", "mem_gb_hours": "mem_gb_hour"}


def generate(seed=17, days=30):
    rng = np.random.default_rng(seed)
    rows = []
    for day in pd.date_range("2026-10-01", periods=days, freq="D"):
        for namespace, models in MODELS.items():
            for model in models:
                gpu = namespace in ("eta-train", "search") or (namespace == "tmp-notebooks" and model == "scratch")
                rows.append({
                    "date": day.strftime("%Y-%m-%d"), "namespace": namespace, "model": model,
                    "workload": WORKLOAD.get(namespace, "serve"),
                    "cpu_hours": round(float(rng.uniform(5, 60)), 3),
                    "gpu_hours": round(float(rng.uniform(0.5, 8)), 3) if gpu else 0.0,
                    "mem_gb_hours": round(float(rng.uniform(40, 400)), 3),
                })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def cost():
    return ex.module("cost.py")


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    frame = generate()
    path = tmp_path_factory.mktemp("usage") / "usage.csv"
    frame.to_csv(path, index=False)
    used = frame[COLUMNS].sum()
    capacity = {"cpu_hours": float(used["cpu_hours"] * 1.6), "gpu_hours": float(used["gpu_hours"] * 2.5),
                "mem_gb_hours": float(used["mem_gb_hours"] * 1.3)}
    config = {"prices": PRICES, "capacity": capacity, "namespaces": NAMESPACES, "cost_centers": COST_CENTERS}
    return path, frame, config


def expected_frame(frame):
    out = frame.copy()
    out["cost"] = sum(out[c] * PRICES[PRICE_OF[c]] for c in COLUMNS)
    out["team"] = out["namespace"].map(NAMESPACES).fillna("unallocated")
    out["model_key"] = out["model"].replace("", np.nan).fillna("unlabelled")
    return out


def expected_idle(frame, capacity):
    return sum(max(0.0, capacity[c] - frame[c].sum()) * PRICES[PRICE_OF[c]] for c in COLUMNS)


def test_load_usage(cost, data):
    path, frame, _ = data
    rows = cost.load_usage(path)
    assert len(rows) == len(frame)
    first = rows[0]
    assert first["namespace"] == "eta-prod" and first["model"] == "eta-duration"
    assert first["cpu_hours"] == pytest.approx(frame.iloc[0]["cpu_hours"])
    assert isinstance(first["gpu_hours"], float)
    blank = [r for r in rows if r["namespace"] == "eta-train" and r["model"] is None]
    assert len(blank) == 30


def test_row_cost(cost):
    row = {"cpu_hours": 10.0, "gpu_hours": 2.0, "mem_gb_hours": 100.0}
    assert cost.row_cost(row, PRICES) == pytest.approx(10 * 0.031 + 2 * 0.90 + 100 * 0.004)


def test_cost_by_model(cost, data):
    path, frame, config = data
    got = cost.cost_by_model(cost.load_usage(path), config)
    expected = expected_frame(frame).groupby(["team", "model_key"])["cost"].sum().to_dict()
    assert set(got) == set(expected)
    for key, value in expected.items():
        assert got[key] == pytest.approx(value), key
    assert ("unallocated", "unlabelled") in got and ("eta", "unlabelled") in got


def test_idle_cost(cost, data):
    path, frame, config = data
    assert cost.idle_cost(cost.load_usage(path), config) == pytest.approx(expected_idle(frame, config["capacity"]))


def test_idle_never_negative_per_resource(cost, data):
    path, frame, config = data
    over = dict(config, capacity={**config["capacity"], "cpu_hours": float(frame["cpu_hours"].sum() * 0.5)})
    expected = sum(max(0.0, over["capacity"][c] - frame[c].sum()) * PRICES[PRICE_OF[c]] for c in COLUMNS)
    assert cost.idle_cost(cost.load_usage(path), over) == pytest.approx(expected)


def test_showback_spreads_idle_by_direct_cost(cost, data):
    path, frame, config = data
    report = cost.showback(cost.load_usage(path), config)
    exp = expected_frame(frame)
    direct = exp.groupby("team")["cost"].sum()
    idle = expected_idle(frame, config["capacity"])
    allocated = direct.drop("unallocated")
    assert set(report) == set(direct.index)
    for team, value in direct.items():
        share = 0.0 if team == "unallocated" else idle * value / allocated.sum()
        assert report[team]["direct"] == pytest.approx(value), team
        assert report[team]["idle_share"] == pytest.approx(share), team
        assert report[team]["total"] == pytest.approx(value + share), team


def test_showback_conserves_provisioned_cost(cost, data):
    path, _, config = data
    report = cost.showback(cost.load_usage(path), config)
    provisioned = sum(config["capacity"][c] * PRICES[PRICE_OF[c]] for c in COLUMNS)
    assert sum(item["total"] for item in report.values()) == pytest.approx(provisioned)


def test_chargeback_lines(cost, data):
    path, frame, config = data
    lines = cost.chargeback(cost.load_usage(path), config)
    report = cost.showback(cost.load_usage(path), config)
    assert [line["cost_center"] for line in lines] == sorted(line["cost_center"] for line in lines)
    by_team = {line["team"]: line for line in lines}
    assert set(by_team) == set(COST_CENTERS) | {"unallocated"}
    assert by_team["unallocated"]["cost_center"] == "UNALLOCATED"
    for team, center in COST_CENTERS.items():
        assert by_team[team]["cost_center"] == center
        assert by_team[team]["amount"] == round(report[team]["total"], 2)


def test_tiny_example_by_hand(cost, tmp_path):
    path = tmp_path / "u.csv"
    path.write_text(
        "date,namespace,model,workload,cpu_hours,gpu_hours,mem_gb_hours\n"
        "2026-10-01,eta-prod,eta-duration,serve,100,0,0\n"
        "2026-10-01,search,search-ranker,serve,0,10,0\n"
        "2026-10-01,tmp-notebooks,,notebook,50,0,0\n",
        encoding="utf-8",
    )
    config = {"prices": {"cpu_hour": 0.1, "gpu_hour": 1.0, "mem_gb_hour": 0.0},
              "capacity": {"cpu_hours": 250, "gpu_hours": 20, "mem_gb_hours": 0}, "namespaces": NAMESPACES,
              "cost_centers": COST_CENTERS}
    rows = cost.load_usage(path)
    assert cost.idle_cost(rows, config) == pytest.approx(20.0)
    report = cost.showback(rows, config)
    assert report["eta"] == pytest.approx({"direct": 10.0, "idle_share": 10.0, "total": 20.0})
    assert report["search"] == pytest.approx({"direct": 10.0, "idle_share": 10.0, "total": 20.0})
    assert report["unallocated"] == pytest.approx({"direct": 5.0, "idle_share": 0.0, "total": 5.0})
