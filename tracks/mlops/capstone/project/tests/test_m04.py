"""M04: cổng promotion, registry, alias champion và rollback. Đề ở capstone/milestones/m04-registry-promotion.md."""

import uuid

import numpy as np
import pytest
from etakit import need

import mlopskit

BASE = {"mae": 150.0, "p90_abs_err": 320.0, "mae_airport": 300.0}


@pytest.mark.parametrize(
    "challenger, champion, policy, promote, mention",
    [
        ({"mae": 140.0, "p90_abs_err": 300.0, "mae_airport": 290.0}, BASE, {}, True, None),
        ({"mae": 140.0, "p90_abs_err": 300.0, "mae_airport": 330.0}, BASE, {}, False, "airport"),
        ({"mae": 140.0, "p90_abs_err": 300.0, "mae_airport": 309.0}, BASE, {}, True, None),
        ({"mae": 151.0, "p90_abs_err": 300.0, "mae_airport": 280.0}, BASE, {}, False, "mae"),
        ({"mae": 150.0, "p90_abs_err": 330.0, "mae_airport": 300.0}, BASE, {}, True, None),
        ({"mae": 152.0, "p90_abs_err": 300.0, "mae_airport": 300.0}, BASE, {"max_mae_regression": 0.02}, True, None),
        ({"mae": 140.0, "p90_abs_err": 300.0, "mae_airport": 290.0}, None, {}, True, None),
        ({"mae": 140.0, "p90_abs_err": 300.0, "mae_airport": 290.0}, {"p90_abs_err": 320.0, "mae_airport": 300.0}, {}, False, "mae"),
        ({"mae": 140.0, "p90_abs_err": 300.0, "mae_airport": 290.0}, {**BASE, "mae": float("nan")}, {}, False, "mae"),
    ],
    ids=["better", "airport-10pct-worse", "airport-3pct-worse", "mae-worse", "equal", "mae-within-policy", "no-champion",
         "champion-mae-missing", "champion-mae-nan"],
)
def test_m04_promotion_rules(project, challenger, champion, policy, promote, mention):
    promotion = need("promotion", "Policy", "decide")
    decision = promotion.decide(challenger, champion, promotion.Policy(**policy))
    assert decision.promote is promote, decision.reasons
    assert decision.reasons and all(isinstance(r, str) for r in decision.reasons), "reasons phải là list[str] không rỗng"
    if mention:
        assert mention in " ".join(decision.reasons).lower(), f"reasons phải nhắc '{mention}': {decision.reasons}"


def test_m04_alias_rollback(project, tmp_path, synthetic_trips, monkeypatch):
    mlopskit.require_stack("mlflow")
    import mlflow
    from fastapi.testclient import TestClient
    from mlflow import MlflowClient

    config = need("config", "Config")
    features = need("features", "build_features")
    train = need("train", "train")
    registry = need("registry", "log_and_register")
    promotion = need("promotion", "Policy", "promote_if_better")
    uri = f"http://127.0.0.1:{mlopskit.stack_port('mlflow')}"
    name = f"eta-test-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.setenv("MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD", "false")
    monkeypatch.delenv("ETA_MODEL_PATH", raising=False)
    mlflow.set_tracking_uri(uri)
    client = MlflowClient(tracking_uri=uri)
    X, y = features.build_features(synthetic_trips)
    weak = train.train(X, y, {"max_iter": 3, "random_state": 0})
    strong = train.train(X, y, {"max_iter": 60, "random_state": 0})
    cfg = config.Config(data_dir=tmp_path, months=["2019-01"], sample_rows=6_000, seed=0,
                        model_params={"max_iter": 3}, mlflow_uri=uri, model_name=name)
    try:
        v1 = registry.log_and_register(weak, {"mae": 200.0, "p90_abs_err": 420.0, "mae_airport": 320.0}, cfg, "test-data-v1")
        assert promotion.promote_if_better(name, v1, promotion.Policy()).promote
        assert client.get_model_version_by_alias(name, "champion").version == str(v1)
        cfg.model_params = {"max_iter": 60}
        v2 = registry.log_and_register(strong, {"mae": 150.0, "p90_abs_err": 330.0, "mae_airport": 280.0}, cfg, "test-data-v2")
        assert str(v2) != str(v1)
        tags = client.get_model_version(name, str(v2)).tags
        assert tags.get("data_version") == "test-data-v2" and tags.get("git_commit"), f"version thiếu tag lineage: {tags}"
        assert promotion.promote_if_better(name, v2, promotion.Policy()).promote
        assert client.get_model_version_by_alias(name, "champion").version == str(v2)
        v3 = registry.log_and_register(strong, {"mae": 140.0, "p90_abs_err": 320.0, "mae_airport": 320.0}, cfg, "test-data-v3")
        rejected = promotion.promote_if_better(name, v3, promotion.Policy())
        assert not rejected.promote and "airport" in " ".join(rejected.reasons).lower()
        assert client.get_model_version_by_alias(name, "champion").version == str(v2), "bị chặn thì alias giữ nguyên"
        client.set_registered_model_alias(name, "champion", str(v1))
        champion = mlflow.sklearn.load_model(f"models:/{name}@champion")
        assert np.array_equal(champion.predict(X), weak.predict(X)), "sau rollback, champion phải dự đoán đúng như v1"
        assert not np.array_equal(champion.predict(X), strong.predict(X))
        monkeypatch.setenv("ETA_MODEL_NAME", name)
        serve = need("serve", "app")
        with TestClient(serve.app) as api:
            assert api.get("/healthz").json().get("model_version") == str(v1)
            body = api.post("/predict", json={"PULocationID": 161, "DOLocationID": 236,
                                              "pickup_datetime": "2019-01-15T08:30:00", "trip_distance": 2.4}).json()
            assert body["model_version"] == str(v1) and body["eta_s"] > 0
    finally:
        for cleanup in (lambda: client.delete_registered_model(name),
                        lambda: client.delete_experiment(client.get_experiment_by_name(name).experiment_id)):
            try:
                cleanup()
            except Exception:
                pass
