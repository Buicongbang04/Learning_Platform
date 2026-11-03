import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ.setdefault("MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD", "false")

import json
import uuid
from types import SimpleNamespace

import mlflow
import numpy as np
import pytest
from mlflow import MlflowClient
from sklearn.dummy import DummyRegressor

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
X = np.zeros((2, 2))
GOOD_TAGS = {"git_commit": "a" * 40, "git_dirty": "false", "data_version": "c0ffee01"}


def decide(challenger, champion, policy):
    calls.append((challenger, champion, policy))
    if champion is None:
        return SimpleNamespace(promote=True, reasons=["chưa có champion"])
    reasons = []
    if challenger["mae"] > champion["mae"] * 0.99:
        reasons.append("MAE tổng không đủ tốt hơn")
    for name, base in champion["slices"].items():
        if challenger["slices"][name]["mae"] > base["mae"] * 1.05:
            reasons.append(f"slice '{name}' xấu đi")
    return SimpleNamespace(promote=not reasons, reasons=reasons or ["đạt"])


calls: list = []


@pytest.fixture(scope="module")
def gate():
    return ex.module("gate.py")


@pytest.fixture(scope="module")
def env():
    mlopskit.require_stack("mlflow", "postgres", "minio")
    uri = f"http://127.0.0.1:{mlopskit.stack_port('mlflow')}"
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(uri)
    client = MlflowClient(uri)
    tag = uuid.uuid4().hex[:8]
    experiment = client.create_experiment(f"mlops-ex-{tag}")
    names = []

    def make(mae, airport, tags=None, latency=40.0, model=None):
        if model is None:
            model = f"mlops-ex-{tag}-{len(names)}"
            names.append(model)
            client.create_registered_model(model)
        with mlflow.start_run(experiment_id=experiment, tags=GOOD_TAGS if tags is None else tags) as run:
            mlflow.log_metrics({"mae": mae, "latency_p95_ms": latency, "mae_slice.airport": airport,
                                "n_slice.airport": 5000, "mae_slice.night": 250.0, "n_slice.night": 3000})
            info = mlflow.sklearn.log_model(DummyRegressor(strategy="constant", constant=mae).fit(X, [mae] * 2),
                                            name="model", input_example=X[:1])
        mv = client.create_model_version(model, info.model_uri, run.info.run_id, model_id=info.model_id)
        return model, int(mv.version)

    try:
        yield client, make
    finally:
        for name in names:
            try:
                client.delete_registered_model(name)
            except Exception:
                pass
        client.delete_experiment(experiment)
        mlflow.set_tracking_uri(previous)


def alias_version(client, model, alias="champion"):
    try:
        return int(client.get_model_version_by_alias(model, alias).version)
    except Exception:
        return None


def test_collect_metrics_shape(gate, env):
    client, make = env
    model, v = make(200.0, 300.0)
    assert gate.collect_metrics(client, model, v) == {
        "mae": 200.0, "latency_p95_ms": 40.0,
        "slices": {"airport": {"mae": 300.0, "n": 5000}, "night": {"mae": 250.0, "n": 3000}}}


def test_lineage_problems(gate, env):
    client, make = env
    model, good = make(200.0, 300.0)
    assert gate.lineage_problems(client, model, good) == []
    _, dirty = make(200.0, 300.0, tags={**GOOD_TAGS, "git_dirty": "true"}, model=model)
    assert any("git_dirty" in p for p in gate.lineage_problems(client, model, dirty))
    _, bare = make(200.0, 300.0, tags={"git_commit": "a" * 40}, model=model)
    problems = gate.lineage_problems(client, model, bare)
    assert any("data_version" in p for p in problems) and not any("git_commit" in p for p in problems)


def test_first_model_is_promoted_without_champion(gate, env):
    client, make = env
    model, v1 = make(200.0, 300.0)
    calls.clear()
    result = gate.gate_and_promote(client, model, v1, decide)
    assert result["promoted"] is True and result["version"] == v1
    assert calls[0][1] is None
    assert alias_version(client, model) == v1
    tags = client.get_model_version(model, str(v1)).tags
    assert tags["promotion.decision"] == "promoted"
    assert tags["promotion.compared_to"] == "none"
    assert "previous_champion" not in tags


def test_better_model_promoted_and_decision_recorded(gate, env):
    client, make = env
    model, v1 = make(200.0, 300.0)
    gate.gate_and_promote(client, model, v1, decide)
    _, v2 = make(180.0, 290.0, model=model)
    result = gate.gate_and_promote(client, model, v2, decide, policy={"x": 1})
    assert result["promoted"] is True
    assert alias_version(client, model) == v2
    new, old = (client.get_model_version(model, str(v)).tags for v in (v2, v1))
    assert new["promotion.decision"] == "promoted"
    assert new["promotion.compared_to"] == str(v1)
    assert new["previous_champion"] == str(v1)
    assert json.loads(new["promotion.reasons"]) == result["reasons"]
    assert old["superseded_by"] == str(v2)
    assert calls[-1][2] == {"x": 1}


def test_slice_regression_is_rejected_and_alias_stays(gate, env):
    client, make = env
    model, v1 = make(200.0, 300.0)
    gate.gate_and_promote(client, model, v1, decide)
    _, v2 = make(170.0, 400.0, model=model)
    result = gate.gate_and_promote(client, model, v2, decide)
    assert result["promoted"] is False
    assert alias_version(client, model) == v1
    tags = client.get_model_version(model, str(v2)).tags
    assert tags["promotion.decision"] == "rejected"
    assert any("airport" in r for r in json.loads(tags["promotion.reasons"]))
    assert "previous_champion" not in tags
    assert "superseded_by" not in client.get_model_version(model, str(v1)).tags


def test_dirty_tree_blocks_even_a_better_model(gate, env):
    client, make = env
    model, v1 = make(200.0, 300.0)
    gate.gate_and_promote(client, model, v1, decide)
    _, v2 = make(150.0, 250.0, tags={**GOOD_TAGS, "git_dirty": "true"}, model=model)
    result = gate.gate_and_promote(client, model, v2, decide)
    assert result["promoted"] is False
    assert alias_version(client, model) == v1
    assert any("git_dirty" in r for r in result["reasons"])
    assert client.get_model_version(model, str(v2)).tags["promotion.decision"] == "rejected"


def test_champion_cannot_be_gated_against_itself(gate, env):
    client, make = env
    model, v1 = make(200.0, 300.0)
    gate.gate_and_promote(client, model, v1, decide)
    with pytest.raises(ValueError):
        gate.gate_and_promote(client, model, v1, decide)
