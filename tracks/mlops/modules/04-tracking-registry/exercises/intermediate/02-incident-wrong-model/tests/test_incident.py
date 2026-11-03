import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow
import numpy as np
import pytest
from mlflow import MlflowClient
from sklearn.dummy import DummyRegressor

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
X = np.zeros((3, 2))
MODEL = "taxi-eta"


@pytest.fixture
def service_mod():
    return ex.module("service.py")


@pytest.fixture
def registry(tmp_path):
    uri = mlopskit.mlflow_local(tmp_path)
    client = MlflowClient(uri)
    client.create_registered_model(MODEL)

    def add(constant):
        with mlflow.start_run() as run:
            info = mlflow.sklearn.log_model(DummyRegressor(strategy="constant", constant=constant).fit(X, [constant] * 3),
                                            name="model", input_example=X[:1])
        mv = client.create_model_version(MODEL, info.model_uri, run.info.run_id, model_id=info.model_id)
        return int(mv.version)

    return uri, client, add


@pytest.fixture
def staged(registry):
    uri, client, add = registry
    v1, v2, v3 = add(600.0), add(620.0), add(999.0)
    client.set_registered_model_alias(MODEL, "champion", str(v2))
    return uri, client, add, (v1, v2, v3)


def test_service_serves_approved_model_not_newest(service_mod, staged):
    uri, _, _, (v1, v2, v3) = staged
    svc = service_mod.ModelService(uri, MODEL)
    assert svc.version == v2
    assert svc.predict(X) == {"model_version": v2, "predictions": [620.0] * 3}


def test_new_unapproved_version_does_not_change_served_model(service_mod, staged):
    uri, _, add, (_, v2, _) = staged
    svc = service_mod.ModelService(uri, MODEL)
    add(1.0)
    assert svc.refresh() is False
    assert svc.version == v2
    assert svc.predict(X)["predictions"][0] == 620.0


def test_restart_after_new_unapproved_version_serves_same_model(service_mod, staged):
    uri, _, add, (_, v2, _) = staged
    add(1.0)
    assert service_mod.ModelService(uri, MODEL).version == v2


def test_refresh_follows_approval_changes_including_rollback(service_mod, staged):
    uri, client, _, (v1, v2, _) = staged
    svc = service_mod.ModelService(uri, MODEL)
    client.set_registered_model_alias(MODEL, "champion", str(v1))
    assert svc.refresh() is True
    assert svc.version == v1
    assert svc.predict(X)["predictions"][0] == 600.0
    assert svc.refresh() is False


def test_refuses_to_start_without_approved_model(service_mod, registry):
    uri, _, add = registry
    add(999.0)
    with pytest.raises(LookupError):
        service_mod.ModelService(uri, MODEL)


def test_failed_refresh_keeps_serving_current_model(service_mod, staged):
    uri, client, _, (_, v2, _) = staged
    svc = service_mod.ModelService(uri, MODEL)
    client.delete_registered_model_alias(MODEL, "champion")
    with pytest.raises(LookupError):
        svc.refresh()
    assert svc.version == v2
    assert svc.predict(X)["predictions"][0] == 620.0
