"""M02: image serving, image training, stack Compose. Đề ở capstone/milestones/m02-containers.md."""

import json
import uuid

import httpx
import joblib
from etakit import need, require_file, synthetic_month

import mlopskit
from testkit import DockerLab

TRIP = {"PULocationID": 161, "DOLocationID": 236, "pickup_datetime": "2019-01-15T08:30:00", "trip_distance": 2.4}
MAX_IMAGE_MB = 1536


def saved_model(tmp_path, synthetic_trips):
    features = need("features", "build_features")
    train = need("train", "train")
    X, y = features.build_features(synthetic_trips)
    folder = tmp_path / "models"
    folder.mkdir()
    folder.chmod(0o755)
    joblib.dump(train.train(X, y, {"max_iter": 30, "random_state": 0}), folder / "model.joblib")
    (folder / "model.joblib").chmod(0o644)
    return folder


def check_api(base: str) -> None:
    health = httpx.get(f"{base}/healthz", timeout=10)
    assert health.status_code == 200, health.text
    reply = httpx.post(f"{base}/predict", json=TRIP, timeout=10)
    assert reply.status_code == 200, reply.text
    body = reply.json()
    assert isinstance(body.get("eta_s"), float) and body["eta_s"] > 0, body
    assert isinstance(body.get("model_version"), str) and body["model_version"], body
    bad = httpx.post(f"{base}/predict", json={**TRIP, "PULocationID": 0}, timeout=10)
    assert bad.status_code == 422, f"zone 0 phải bị từ chối với 422, nhận {bad.status_code}"


def test_m02_serve_image(project, tmp_path, synthetic_trips):
    require_file("Dockerfile.serve")
    models = saved_model(tmp_path, synthetic_trips)
    with mlopskit.built_image(project, "Dockerfile.serve") as tag, DockerLab() as lab:
        lab.start("api", tag, ports=[8000], mounts=[(models, "/models")],
                  env={"ETA_MODEL_PATH": "/models/model.joblib"}, memory="512m")
        base = f"http://127.0.0.1:{lab.port('api', 8000)}"
        lab.wait_http("api", f"{base}/healthz", timeout=90)
        check_api(base)
        uid = lab.exec("api", "id", "-u")
        assert uid.returncode == 0 and uid.stdout.strip() != "0", "container serving phải chạy bằng user không phải root"


def test_m02_train_image_small(project, tmp_path):
    require_file("Dockerfile.train")
    data = tmp_path / "data"
    data.mkdir()
    data.chmod(0o755)
    synthetic_month(3_000, seed=4).to_parquet(data / "yellow_tripdata_2019-01.parquet", index=False)
    (data / "config.yaml").write_text(
        "data_dir: /data\nmonths: [\"2019-01\"]\nsample_rows: 2000\nseed: 0\nmodel_params:\n  max_iter: 30\n"
        "mlflow_uri: http://127.0.0.1:9\nmodel_name: eta\n",
        encoding="utf-8",
    )
    for path in data.iterdir():
        path.chmod(0o644)
    with mlopskit.built_image(project, "Dockerfile.train") as tag, DockerLab() as lab:
        lab.start("train", tag, "infinity", entrypoint="sleep", mounts=[(data, "/data")], memory="1g")
        run = lab.exec("train", "python", "-m", "eta.cli", "train", "--config", "/data/config.yaml", timeout=240)
        assert run.returncode == 0, run.stderr[-2000:]
        assert "mae" in json.loads(run.stdout.strip().splitlines()[-1])
        torch = lab.exec("train", "python", "-c", "import importlib.util as u; print(u.find_spec('torch') is None)")
        assert torch.stdout.strip() == "True", "image training không được có torch"
        size = lab.exec("train", "du", "-sxm", "/", timeout=120)
        megabytes = int(size.stdout.split()[0])
        assert megabytes < MAX_IMAGE_MB, f"image training {megabytes} MB, cần < {MAX_IMAGE_MB} MB"
        uid = lab.exec("train", "id", "-u")
        assert uid.stdout.strip() != "0", "container training phải chạy bằng user không phải root"


def register_champion(uri: str, name: str, model) -> str:
    import mlflow
    import skops.io
    from mlflow import MlflowClient

    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(name)
    trusted = skops.io.get_untrusted_types(data=skops.io.dumps(model))
    with mlflow.start_run():
        info = mlflow.sklearn.log_model(model, name="model", registered_model_name=name, skops_trusted_types=trusted,
                                        pip_requirements=["scikit-learn"])
    version = str(info.registered_model_version)
    MlflowClient(tracking_uri=uri).set_registered_model_alias(name, "champion", version)
    return version


def drop_registered(uri: str, name: str) -> None:
    from mlflow import MlflowClient

    client = MlflowClient(tracking_uri=uri)
    try:
        client.delete_registered_model(name)
    except Exception:
        pass
    try:
        experiment = client.get_experiment_by_name(name)
        if experiment is not None:
            client.delete_experiment(experiment.experiment_id)
    except Exception:
        pass


def test_m02_compose_api(project, tmp_path, synthetic_trips, monkeypatch):
    compose = require_file("compose.yaml")
    mlopskit.require_stack("mlflow")
    features = need("features", "build_features")
    train = need("train", "train")
    X, y = features.build_features(synthetic_trips)
    model = train.train(X, y, {"max_iter": 30, "random_state": 0})
    uri = f"http://127.0.0.1:{mlopskit.stack_port('mlflow')}"
    name = f"eta-compose-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD", "false")
    empty = tmp_path / "empty"
    empty.mkdir()
    empty.chmod(0o755)
    try:
        version = register_champion(uri, name, model)
        env = {"ETA_MODEL_NAME": name, "ETA_MODEL_PATH": "", "ETA_MODEL_DIR": str(empty), "ETA_API_PORT": "0"}
        with mlopskit.compose_project(compose, env=env) as stack:
            base = f"http://127.0.0.1:{stack.port('api', 8000)}"
            check_api(base)
            reported = httpx.get(f"{base}/healthz", timeout=10).json().get("model_version")
            assert reported == version, f"API phải nạp models:/{name}@champion (version {version}) từ MLflow của stack, báo {reported}"
    finally:
        drop_registered(uri, name)
