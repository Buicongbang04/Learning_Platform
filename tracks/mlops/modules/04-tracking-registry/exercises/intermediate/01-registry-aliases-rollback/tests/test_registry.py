import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ.setdefault("MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD", "false")

import uuid

import mlflow
import numpy as np
import pytest
from mlflow import MlflowClient
from sklearn.dummy import DummyRegressor

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
X = np.zeros((2, 2))


@pytest.fixture(scope="module")
def reg():
    return ex.module("registry.py")


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

    def new_name():
        names.append(f"mlops-ex-{tag}-{len(names)}")
        return names[-1]

    def log_model(constant):
        with mlflow.start_run(experiment_id=experiment) as run:
            info = mlflow.sklearn.log_model(DummyRegressor(strategy="constant", constant=constant).fit(X, [constant] * 2),
                                            name="model", input_example=X[:1])
        return info.model_uri, info.model_id, run.info.run_id

    try:
        yield client, new_name, log_model
    finally:
        for name in names:
            try:
                client.delete_registered_model(name)
            except Exception:
                pass
        client.delete_experiment(experiment)
        mlflow.set_tracking_uri(previous)


@pytest.fixture(scope="module")
def three(env):
    client, new_name, log_model = env
    name = new_name()
    client.create_registered_model(name)
    for constant in (10.0, 20.0, 30.0):
        uri, model_id, run_id = log_model(constant)
        client.create_model_version(name, uri, run_id, model_id=model_id)
    return client, name, [1, 2, 3]


def test_register_versions_increase_and_keep_tags(env, reg):
    client, new_name, log_model = env
    name = new_name()
    versions = [reg.register_version(client, name, *log_model(c), {"approved": "yes"}) for c in (10.0, 20.0)]
    assert versions == [1, 2]
    assert all(isinstance(v, int) for v in versions)
    mv = client.get_model_version(name, "2")
    assert mv.tags["approved"] == "yes"
    assert mv.status == "READY"
    assert mv.run_id


def test_promote_first_version_has_no_previous(env, reg, three):
    client, name, v = three
    assert reg.promote(client, name, v[0], alias="solo") is None
    assert client.get_model_version_by_alias(name, "solo").version == "1"
    assert "previous_solo" not in client.get_model_version(name, "1").tags


def test_promote_records_previous_and_rollback_restores(env, reg, three):
    client, name, v = three
    alias = "flow"
    reg.promote(client, name, v[0], alias=alias)
    assert reg.promote(client, name, v[1], alias=alias) == 1
    assert client.get_model_version(name, "2").tags[f"previous_{alias}"] == "1"

    model, version = reg.load_by_alias(client, name, alias)
    assert version == 2
    assert model.predict(X)[0] == 20.0

    assert reg.rollback(client, name, alias) == 1
    assert client.get_model_version_by_alias(name, alias).version == "1"
    assert client.get_model_version(name, "2").tags["rolled_back"] == "true"
    model, version = reg.load_by_alias(client, name, alias)
    assert version == 1
    assert model.predict(X)[0] == 10.0


def test_rollback_twice_has_no_second_way_back(env, reg, three):
    client, name, v = three
    alias = "twice"
    reg.promote(client, name, v[0], alias=alias)
    reg.promote(client, name, v[2], alias=alias)
    reg.rollback(client, name, alias)
    with pytest.raises(LookupError):
        reg.rollback(client, name, alias)


def test_rollback_without_alias_raises(env, reg, three):
    client, name, _ = three
    with pytest.raises(LookupError):
        reg.rollback(client, name, "never-set")


def test_loaded_version_is_not_affected_by_later_alias_change(env, reg, three):
    client, name, v = three
    alias = "pinned"
    reg.promote(client, name, v[0], alias=alias)
    model, version = reg.load_by_alias(client, name, alias)
    reg.promote(client, name, v[2], alias=alias)
    assert version == 1
    assert model.predict(X)[0] == 10.0


def test_register_version_is_safe_on_existing_model(env, reg):
    client, new_name, log_model = env
    name = new_name()
    first = reg.register_version(client, name, *log_model(1.0))
    second = reg.register_version(client, name, *log_model(2.0))
    assert (first, second) == (1, 2)
