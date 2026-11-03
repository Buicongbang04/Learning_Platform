import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import threading
import time

import mlflow
import numpy as np
import pytest
from fastapi.testclient import TestClient
from mlflow import MlflowClient
from sklearn.dummy import DummyRegressor

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
X = np.zeros((3, 3))
MODEL = "taxi-eta"
TOKEN = "s3cret"
ROW = {"rows": [[5, 8, 1]]}


@pytest.fixture
def service():
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

    v1, v2 = add(620.0), add(999.0)
    client.set_registered_model_alias(MODEL, "champion", str(v2))
    return uri, client, (v1, v2)


def post(client, token=TOKEN):
    headers = {"X-Admin-Token": token} if token is not None else {}
    return client.post("/admin/reload", headers=headers)


def test_serves_the_alias_version_with_version_in_response(service, registry):
    uri, _, (v1, v2) = registry
    client = TestClient(service.create_app(uri, MODEL, TOKEN))
    assert client.post("/predict", json=ROW).json() == {"model_version": v2, "predictions": [999.0]}


def test_rollback_by_alias_then_reload_without_restart(service, registry):
    uri, registry_client, (v1, v2) = registry
    client = TestClient(service.create_app(uri, MODEL, TOKEN))
    registry_client.set_registered_model_alias(MODEL, "champion", str(v1))
    assert client.post("/predict", json=ROW).json()["model_version"] == v2, "Đổi alias chưa reload thì service giữ version đã nạp"
    response = post(client)
    assert response.status_code == 200
    assert response.json() == {"changed": True, "previous_version": v2, "model_version": v1}
    assert client.post("/predict", json=ROW).json() == {"model_version": v1, "predictions": [620.0]}


def test_reload_without_change_does_not_reload_the_model(service, registry, monkeypatch):
    uri, _, (_, v2) = registry
    client = TestClient(service.create_app(uri, MODEL, TOKEN))
    calls = []
    original = mlflow.pyfunc.load_model
    monkeypatch.setattr(mlflow.pyfunc, "load_model", lambda *a, **k: calls.append(a) or original(*a, **k))
    assert post(client).json() == {"changed": False, "previous_version": v2, "model_version": v2}
    assert calls == []


@pytest.mark.parametrize("token", [None, "wrong", ""])
def test_reload_requires_admin_token(service, registry, token):
    uri, registry_client, (v1, v2) = registry
    client = TestClient(service.create_app(uri, MODEL, TOKEN))
    registry_client.set_registered_model_alias(MODEL, "champion", str(v1))
    assert post(client, token).status_code == 401
    assert client.post("/predict", json=ROW).json()["model_version"] == v2


def test_failed_reload_keeps_serving_the_old_model(service, registry):
    uri, registry_client, (v1, v2) = registry
    client = TestClient(service.create_app(uri, MODEL, TOKEN))
    registry_client.delete_registered_model_alias(MODEL, "champion")
    response = post(client)
    assert response.status_code == 409
    assert str(v2) in response.text
    assert client.post("/predict", json=ROW).json() == {"model_version": v2, "predictions": [999.0]}


def test_refuses_to_start_without_champion(service, registry):
    uri, registry_client, _ = registry
    registry_client.delete_registered_model_alias(MODEL, "champion")
    with pytest.raises(LookupError):
        service.create_app(uri, MODEL, TOKEN)


def test_requests_during_reload_never_fail_or_mix_versions(service, registry, monkeypatch):
    uri, registry_client, (v1, v2) = registry
    client = TestClient(service.create_app(uri, MODEL, TOKEN))
    registry_client.set_registered_model_alias(MODEL, "champion", str(v1))
    original = mlflow.pyfunc.load_model

    def slow(*args, **kwargs):
        time.sleep(0.4)
        return original(*args, **kwargs)

    monkeypatch.setattr(mlflow.pyfunc, "load_model", slow)
    seen, failures = [], []
    stop = threading.Event()

    def hammer():
        while not stop.is_set():
            response = client.post("/predict", json=ROW)
            if response.status_code != 200:
                failures.append(response.status_code)
                continue
            body = response.json()
            seen.append((body["model_version"], body["predictions"][0]))

    thread = threading.Thread(target=hammer)
    thread.start()
    try:
        time.sleep(0.1)
        reloaded = post(client).status_code
        time.sleep(0.1)
    finally:
        stop.set()
        thread.join(timeout=10)
    assert reloaded == 200
    assert not failures, f"Có request lỗi trong lúc reload: {failures}"
    assert {pair for pair in seen} <= {(v2, 999.0), (v1, 620.0)}, "version và dự đoán lệch nhau"
    assert (v2, 999.0) in seen and (v1, 620.0) in seen, "Cần thấy cả version cũ (trong lúc nạp) lẫn version mới (sau reload)"
