"""M07: readiness, canary, shadow, fallback, reload/rollback, log dự đoán, k6. Đề ở capstone/milestones/m07-serving-canary.md."""

import json
import random

import joblib
import pandas as pd
import pytest
from etakit import PREDICTION_LOG_COLUMNS, PROJECT, local_registry, need, require_file

import mlopskit
from testkit import DockerLab

TRIP = {"PULocationID": 161, "DOLocationID": 236, "pickup_datetime": "2019-01-15T08:30:00", "trip_distance": 2.4}


@pytest.fixture(scope="module")
def models(tmp_path_factory):
    folder = tmp_path_factory.mktemp("models")
    folder.chmod(0o755)
    return folder


def build_models(folder, trips) -> None:
    """Champion, challenger (khác champion) và một model hỏng (học trên cột khác) cho các test M07."""
    from sklearn.linear_model import LinearRegression

    if (folder / "broken.joblib").is_file():
        return
    features = need("features", "build_features")
    train = need("train", "train")
    X, y = features.build_features(trips)
    joblib.dump(train.train(X, y, {"max_iter": 30, "random_state": 0}), folder / "champion.joblib")
    joblib.dump(train.train(X, y, {"max_iter": 4, "random_state": 0}), folder / "challenger.joblib")
    joblib.dump(LinearRegression().fit(pd.DataFrame({"x": [0.0, 1.0, 2.0]}), [1.0, 2.0, 3.0]), folder / "broken.joblib")
    for path in folder.iterdir():
        path.chmod(0o644)


@pytest.fixture
def serve_env(monkeypatch, models, tmp_path, synthetic_trips):
    for key in ("ETA_CHALLENGER_PATH", "ETA_CANARY_WEIGHT", "ETA_SHADOW", "ETA_ADMIN_TOKEN", "ETA_SPEED_TABLE"):
        monkeypatch.delenv(key, raising=False)
    log = tmp_path / "predictions.jsonl"
    env = {"ETA_MODEL_PATH": str(models / "champion.joblib"), "ETA_MODEL_VERSION": "v1",
           "ETA_CHALLENGER_VERSION": "v2", "ETA_PREDICTION_LOG": str(log)}
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    def configure(**extra: str):
        build_models(models, synthetic_trips)
        for key, value in extra.items():
            monkeypatch.setenv(key, value)
        return log

    return configure


def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def metric(api, name: str) -> float:
    reply = api.get("/metrics")
    assert reply.status_code == 200, "cần GET /metrics dạng text Prometheus"
    for line in reply.text.splitlines():
        if line.startswith(f"{name} ") or line.startswith(f"{name}{{"):
            return float(line.rsplit(" ", 1)[1])
    return 0.0


def test_m07_readyz_before_load(project, serve_env):
    serve = need("serve", "app")
    serve_env()
    assert client(serve.app).get("/readyz").status_code == 503, "chưa chạy lifespan (chưa nạp model) thì /readyz trả 503"
    with client(serve.app) as api:
        ready = api.get("/readyz")
        assert ready.status_code == 200, ready.text
        assert ready.json().get("model_version") == "v1"
        assert api.get("/healthz").status_code == 200
    assert client(serve.app).get("/readyz").status_code == 503, "sau khi tắt (hết lifespan) /readyz phải về 503"


def test_m07_readyz_needs_speed_table(project, serve_env, synthetic_trips, tmp_path):
    serve = need("serve", "app")
    zf = need("zone_features", "zone_hour_speed", "attach_speed")
    features = need("features", "build_features")
    train = need("train", "train")
    table = zf.zone_hour_speed(synthetic_trips, "2018-12")
    X, y = features.build_features(zf.attach_speed(synthetic_trips, table))
    path = tmp_path / "speed-model.joblib"
    joblib.dump(train.train(X, y, {"max_iter": 10, "random_state": 0}), path)
    serve_env(ETA_MODEL_PATH=str(path))
    with client(serve.app) as api:
        assert api.get("/healthz").status_code == 200
        assert api.get("/readyz").status_code == 503, "model cần avg_speed_mph mà chưa có ETA_SPEED_TABLE thì không được sẵn sàng"
        assert api.post("/predict", json=TRIP).status_code == 503, "không âm thầm điền mặc định cho mọi request"
    table.to_csv(tmp_path / "speed.csv", index=False)
    serve_env(ETA_SPEED_TABLE=str(tmp_path / "speed.csv"))
    with client(serve.app) as api:
        assert api.get("/readyz").status_code == 200
        reply = api.post("/predict", json=TRIP)
        assert reply.status_code == 200 and reply.json()["eta_s"] > 0, reply.text


def test_m07_canary_split(project, serve_env, models):
    serve = need("serve", "app", "route")
    rng = random.Random(0)
    ids = [f"{rng.getrandbits(64):016x}" for _ in range(2_000)]
    picks = [serve.route(i, 0.1) for i in ids]
    assert set(picks) <= {"champion", "canary"}
    share = picks.count("canary") / len(picks)
    assert 0.07 <= share <= 0.13, f"weight 0.1 mà canary nhận {share:.1%}"
    assert picks == [serve.route(i, 0.1) for i in ids], "cùng request_id phải luôn vào cùng nhánh"
    assert {serve.route(i, 0.0) for i in ids} == {"champion"} and {serve.route(i, 1.0) for i in ids} == {"canary"}
    serve_env(ETA_CHALLENGER_PATH=str(models / "challenger.joblib"), ETA_CANARY_WEIGHT="0.5")
    with client(serve.app) as api:
        for request_id in ids[:40]:
            reply = api.post("/predict", json=TRIP, headers={"X-Request-ID": request_id})
            assert reply.status_code == 200, reply.text
            body = reply.json()
            expected = serve.route(request_id, 0.5)
            assert body["variant"] == expected, f"{request_id}: route() nói {expected}, API trả {body['variant']}"
            assert body["model_version"] == ("v2" if expected == "canary" else "v1")
            assert reply.headers.get("x-request-id") == request_id
        generated = api.post("/predict", json=TRIP)
        assert generated.headers.get("x-request-id"), "thiếu X-Request-ID thì API tự sinh và trả lại trong header"


def test_m07_prediction_log_columns(project, serve_env, models):
    serve = need("serve", "app")
    log = serve_env(ETA_CHALLENGER_PATH=str(models / "challenger.joblib"), ETA_SHADOW="1")
    with client(serve.app) as api:
        for i in range(5):
            assert api.post("/predict", json=TRIP, headers={"X-Request-ID": f"log-{i}"}).status_code == 200
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows and all(list(row) == PREDICTION_LOG_COLUMNS for row in rows), "mỗi dòng log đúng PREDICTION_LOG_COLUMNS, đúng thứ tự"
    served = [r for r in rows if r["variant"] == "champion"]
    shadow = [r for r in rows if r["variant"] == "shadow"]
    assert [r["request_id"] for r in served] == [f"log-{i}" for i in range(5)]
    assert len(shadow) == 5 and {r["model_version"] for r in shadow} == {"v2"}, "shadow ghi log riêng, variant 'shadow'"


def test_m07_shadow_failure_does_not_break(project, serve_env, models):
    serve = need("serve", "app")
    serve_env()
    with client(serve.app) as api:
        baseline = api.post("/predict", json=TRIP).json()["eta_s"]
    serve_env(ETA_CHALLENGER_PATH=str(models / "broken.joblib"), ETA_SHADOW="1")
    with client(serve.app) as api:
        before = metric(api, "eta_shadow_errors_total")
        for _ in range(3):
            reply = api.post("/predict", json=TRIP)
            assert reply.status_code == 200, f"shadow lỗi không được làm hỏng request: {reply.status_code} {reply.text}"
            assert reply.json()["eta_s"] == pytest.approx(baseline) and reply.json()["variant"] == "champion"
        assert metric(api, "eta_shadow_errors_total") - before == 3, "đếm lỗi shadow ở eta_shadow_errors_total"
    serve_env(ETA_SHADOW="0", ETA_CANARY_WEIGHT="1")
    with client(serve.app) as api:
        before = metric(api, "eta_fallback_total")
        for _ in range(3):
            reply = api.post("/predict", json=TRIP)
            assert reply.status_code == 200, f"canary lỗi phải fallback về champion: {reply.status_code} {reply.text}"
            body = reply.json()
            assert body["eta_s"] == pytest.approx(baseline) and body["variant"] == "champion" and body["model_version"] == "v1"
        assert metric(api, "eta_fallback_total") - before == 3, "mỗi lần fallback tăng eta_fallback_total"


def test_m07_reload_rollback(project, tmp_path, synthetic_trips, monkeypatch, serve_env):
    from mlflow import MlflowClient

    serve = need("serve", "app")
    config = need("config", "Config")
    features = need("features", "build_features")
    train = need("train", "train")
    registry = need("registry", "log_and_register")
    uri, name = local_registry(tmp_path, "eta-m07")
    X, y = features.build_features(synthetic_trips)
    cfg = config.Config(data_dir=tmp_path, months=["2019-01"], sample_rows=6_000, seed=0, model_params={},
                        mlflow_uri=uri, model_name=name)
    metrics = {"mae": 150.0, "p90_abs_err": 300.0, "mae_airport": 280.0}
    v1 = registry.log_and_register(train.train(X, y, {"max_iter": 3, "random_state": 0}), metrics, cfg, "d1")
    v2 = registry.log_and_register(train.train(X, y, {"max_iter": 40, "random_state": 0}), metrics, cfg, "d2")
    registry_client = MlflowClient(tracking_uri=uri)
    registry_client.set_registered_model_alias(name, "champion", v1)
    serve_env()
    monkeypatch.delenv("ETA_MODEL_PATH")
    monkeypatch.delenv("ETA_MODEL_VERSION")
    monkeypatch.delenv("ETA_CHALLENGER_VERSION")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.setenv("ETA_MODEL_NAME", name)
    with client(serve.app) as api:
        assert api.get("/readyz").json().get("model_version") == v1
        first = api.post("/predict", json=TRIP).json()
        assert first["model_version"] == v1
        registry_client.set_registered_model_alias(name, "champion", v2)
        registry_client.set_registered_model_alias(name, "challenger", v1)
        assert api.post("/predict", json=TRIP).json()["model_version"] == v1, "không tự nạp lại alias ở mỗi request"
        reloaded = api.post("/admin/reload")
        assert reloaded.status_code == 200, reloaded.text
        assert reloaded.json().get("champion") == v2 and reloaded.json().get("challenger") == v1, reloaded.json()
        assert api.post("/predict", json=TRIP).json()["model_version"] == v2
        registry_client.set_registered_model_alias(name, "champion", v1)
        registry_client.delete_registered_model_alias(name, "challenger")
        back = api.post("/admin/reload").json()
        assert back.get("champion") == v1 and back.get("challenger") is None, back
        again = api.post("/predict", json=TRIP).json()
        assert again["model_version"] == v1 and again["eta_s"] == pytest.approx(first["eta_s"]), "rollback về đúng model v1"
        assert api.get("/readyz").json().get("model_version") == v1


def test_m07_loadtest_thresholds(project, tmp_path, models, synthetic_trips):
    require_file("Dockerfile.serve")
    script = require_file("loadtest", "eta.js")
    build_models(models, synthetic_trips)
    with mlopskit.built_image(project, "Dockerfile.serve") as tag, DockerLab() as lab:
        lab.start("api", tag, ports=[8000], mounts=[(models, "/models")],
                  env={"ETA_MODEL_PATH": "/models/champion.joblib", "ETA_MODEL_VERSION": "v1"}, memory="512m")
        base = f"http://127.0.0.1:{lab.port('api', 8000)}"
        lab.wait_http("api", f"{base}/readyz", timeout=90)
        result = mlopskit.k6_run(script, {"TARGET": base})
    assert result.stdout, f"k6 không xuất summary:\n{result.stderr[-3000:]}"
    summary = json.loads(result.stdout)["metrics"]
    duration = summary.get("http_req_duration", {}).get("thresholds", {})
    failed = summary.get("http_req_failed", {}).get("thresholds", {})
    assert "p(95)<200" in duration, f"eta.js cần threshold http_req_duration p(95)<200, có {duration}"
    assert "rate<0.01" in failed, f"eta.js cần threshold http_req_failed rate<0.01, có {failed}"
    assert summary["http_reqs"]["count"] >= 200, "kịch bản tải quá nhỏ (cần ≥200 request)"
    assert result.returncode == 0, f"k6 trượt ngưỡng (exit {result.returncode}):\n{result.stderr[-3000:]}"
