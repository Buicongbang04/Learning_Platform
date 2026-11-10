"""M12: service ETA trên kind + KServe, pipeline training trên Argo Workflows. Đề ở capstone/milestones/m12-kind-kserve.md."""

import json
import re
import shutil
import string
import time
import uuid
from contextlib import ExitStack

import httpx
import joblib
import pandas as pd
import pytest
import yaml
from etakit import need, require_file, synthetic_month

import mlopskit
import testkit

TRIP = {"PULocationID": 161, "DOLocationID": 236, "pickup_datetime": "2019-01-15T08:30:00", "trip_distance": 2.4}
SERVE_VARS = ("ETA_SERVE_IMAGE", "ETA_CHAMPION_IMAGE", "ETA_CHAMPION_VERSION", "ETA_CHALLENGER_IMAGE",
              "ETA_CHALLENGER_VERSION", "ETA_CANARY_WEIGHT", "ETA_ADMIN_TOKEN")
ISVC = "eta"
DEPLOYMENT = f"{ISVC}-predictor"
SERVICE = f"svc/{ISVC}-predictor"
STEPS = ("validate", "train", "gate")
DATA_CONFIGMAP = "eta-train-data"
MONTH = "2019-03"
ROLLOUT_TIMEOUT = 240
ETA_REL = 1e-4
ETA_ABS = 1.0
MIN_ETA_S = 60.0
SPLIT_IDS = 40
WORKFLOW_TIMEOUT = 360


class Images:
    """Build image một lần cho cả module, chỉ khi test đầu tiên cần; xoá image trên máy khi module xong."""

    def __init__(self, project, folder):
        self.project = project
        self.folder = folder
        self.stack = ExitStack()
        self.cache = {}

    def _load(self, key, context, dockerfile):
        if key not in self.cache:
            tag = self.stack.enter_context(mlopskit.built_image(context, dockerfile))
            mlopskit.kind_load(tag)
            self.cache[key] = tag
        return self.cache[key]

    def serve(self) -> str:
        require_file("Dockerfile.serve")
        return self._load("serve", self.project, "Dockerfile.serve")

    def train(self) -> str:
        require_file("Dockerfile.train")
        return self._load("train", self.project, "Dockerfile.train")

    def model(self, name: str, model) -> str:
        dockerfile = require_file("k8s", "Dockerfile.model")
        context = self.folder / name
        context.mkdir(parents=True, exist_ok=True)
        context.chmod(0o755)
        joblib.dump(model, context / "model.joblib")
        (context / "model.joblib").chmod(0o644)
        shutil.copy(dockerfile, context / "Dockerfile.model")
        return self._load(f"model-{name}", context, "Dockerfile.model")


@pytest.fixture(scope="module")
def images(project, tmp_path_factory):
    images = Images(project, tmp_path_factory.mktemp("m12-images"))
    with images.stack:
        yield images


SERVE_ENV = ("ETA_MODEL_PATH", "ETA_MODEL_VERSION", "ETA_CHALLENGER_PATH", "ETA_CHALLENGER_VERSION", "ETA_CANARY_WEIGHT",
             "ETA_SHADOW", "ETA_ADMIN_TOKEN", "ETA_SPEED_TABLE", "ETA_PREDICTION_LOG", "ETA_MODEL_NAME")


def local_eta(serve, path, version: str) -> float:
    """ETA mà chính `eta.serve` của bạn trả cho TRIP với model này, chạy trên máy bằng TestClient (cùng đường code với pod)."""
    from fastapi.testclient import TestClient

    with pytest.MonkeyPatch.context() as patch:
        for key in SERVE_ENV:
            patch.delenv(key, raising=False)
        patch.setenv("ETA_MODEL_PATH", str(path))
        patch.setenv("ETA_MODEL_VERSION", version)
        with TestClient(serve.app) as api:
            reply = api.post("/predict", json=TRIP)
    assert reply.status_code == 200, f"eta.serve trên máy không chấm được model test: {reply.text}"
    return float(reply.json()["eta_s"])


@pytest.fixture(scope="module")
def models(synthetic_trips, tmp_path_factory):
    """Hai model khác nhau rõ rệt, và ETA mà `eta.serve` của bạn trả cho TRIP với từng model khi chạy trên máy."""
    built = {}

    def get():
        if built:
            return built
        features = need("features", "build_features", "make_features")
        train = need("train", "train")
        serve = need("serve", "app", "route")
        folder = tmp_path_factory.mktemp("m12-models")
        X, y = features.build_features(synthetic_trips)
        trip = pd.DataFrame([{"tpep_pickup_datetime": pd.Timestamp(TRIP["pickup_datetime"]),
                              "PULocationID": TRIP["PULocationID"], "DOLocationID": TRIP["DOLocationID"],
                              "trip_distance": TRIP["trip_distance"]}])
        for name, rounds in (("a", 30), ("b", 3)):
            model = train.train(X, y, {"max_iter": rounds, "random_state": 0})
            joblib.dump(model, folder / f"{name}.joblib")
            eta = local_eta(serve, folder / f"{name}.joblib", name)
            raw = max(float(model.predict(features.make_features(trip))[0]), MIN_ETA_S)
            assert abs(eta - raw) <= ETA_ABS, (
                f"eta.serve trên máy trả {eta:.3f} cho model {name}, model.predict(make_features) cho {raw:.3f} "
                f"(đã kẹp {MIN_ETA_S:.0f} s): /predict phải trả đúng dự đoán của model, lệch tối đa {ETA_ABS} s do làm tròn")
            built[name] = (model, eta)
        assert abs(built["a"][1] - built["b"][1]) > 1, "hai model test phải cho ETA khác nhau"
        built["route"] = serve.route
        return built

    return get


def render(path, **values: str) -> str:
    try:
        return string.Template(path.read_text(encoding="utf-8")).substitute(values)
    except KeyError as err:
        pytest.fail(f"{path.name} dùng biến {err} không có trong danh sách biến của đề", pytrace=False)
    except ValueError as err:
        pytest.fail(f"{path.name}: placeholder sai cú pháp ({err}); đừng dùng ký tự $ ngoài bảy biến release", pytrace=False)


def documents(text: str) -> list[dict]:
    try:
        return [d for d in yaml.safe_load_all(text) if d]
    except yaml.YAMLError as err:
        pytest.fail(f"YAML không hợp lệ sau khi thay biến: {err}", pytrace=False)


def release_values(images, champion: tuple[str, str], challenger: tuple[str, str], weight: float, token: str) -> dict:
    return {"ETA_SERVE_IMAGE": images.serve(), "ETA_CHAMPION_IMAGE": champion[0], "ETA_CHAMPION_VERSION": champion[1],
            "ETA_CHALLENGER_IMAGE": challenger[0], "ETA_CHALLENGER_VERSION": challenger[1],
            "ETA_CANARY_WEIGHT": str(weight), "ETA_ADMIN_TOKEN": token, "ETA_PRIORITY_CLASS": ""}


def deploy(ns: str, manifest, values: dict) -> None:
    mlopskit.apply_manifest(render(manifest, **values), ns)
    generation = mlopskit.kubectl("get", "inferenceservice", ISVC, "-o", "jsonpath={.metadata.generation}",
                                  namespace=ns).stdout.strip()
    if not generation:
        pytest.fail(f"k8s/eta.yaml phải tạo InferenceService tên `{ISVC}`", pytrace=False)
    mlopskit.wait_for("inferenceservice", ISVC, f"jsonpath={{.status.observedGeneration}}={generation}", ns, 120)
    rollout = mlopskit.kubectl("rollout", "status", f"deployment/{DEPLOYMENT}", f"--timeout={ROLLOUT_TIMEOUT}s",
                               namespace=ns, timeout=ROLLOUT_TIMEOUT + 30)
    if rollout.returncode != 0:
        pods = mlopskit.kubectl("get", "pods", "-o", "wide", namespace=ns).stdout
        events = mlopskit.kubectl("get", "events", "--sort-by=.lastTimestamp", namespace=ns).stdout
        pytest.fail(f"deployment/{DEPLOYMENT} không rollout xong sau {ROLLOUT_TIMEOUT} giây: {rollout.stderr[-500:]}\n"
                    f"--- pods\n{pods}\n--- events\n{events[-3000:]}", pytrace=False)
    mlopskit.wait_for("inferenceservice", ISVC, "Ready", ns, ROLLOUT_TIMEOUT)


def release_matches(body, champion: str, challenger: str, weight: float) -> bool:
    """`/readyz` khớp release: champion đúng; `challenger`, `canary_weight` nếu có thì cũng khớp.

    Release không có challenger riêng (challenger trùng champion) thì `challenger: null` cũng được (M07 mục 1).
    """
    if not isinstance(body, dict) or body.get("model_version") != champion:
        return False
    if "challenger" in body:
        allowed = {challenger, None} if challenger == champion else {challenger}
        if body["challenger"] not in allowed:
            return False
    if "canary_weight" in body:
        try:
            return float(body["canary_weight"]) == pytest.approx(weight)
        except (TypeError, ValueError):
            return False
    return True


def serving(ns: str, champion: str, challenger: str, weight: float, timeout: float = 90) -> None:
    """Chờ pod sau Service báo đúng release (pod cũ có thể còn vài giây trong lúc thay)."""
    deadline = time.monotonic() + timeout
    seen = None
    while time.monotonic() < deadline:
        try:
            with mlopskit.port_forward(ns, SERVICE, 80) as port:
                reply = httpx.get(f"http://127.0.0.1:{port}/readyz", timeout=10)
            seen = (reply.status_code, reply.text[:300])
            if reply.status_code == 200 and release_matches(reply.json(), champion, challenger, weight):
                return
        except (httpx.HTTPError, ValueError, pytest.fail.Exception) as err:
            seen = repr(err)[:300]
        time.sleep(3)
    pytest.fail(f"InferenceService Ready nhưng /readyz chưa báo champion {champion}, challenger {challenger}, "
                f"canary_weight {weight} sau {timeout:.0f} giây: {seen}. Biến release có nằm trong pod template không "
                "(đổi ConfigMap không khởi động lại pod)?", pytrace=False)


def check_split(ns: str, route, weight: float, champion: tuple[str, float], challenger: tuple[str, float],
                n: int = SPLIT_IDS) -> None:
    ids = [f"m12-split-{i}" for i in range(n)]
    canary = 0
    with mlopskit.port_forward(ns, SERVICE, 80) as port, httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as api:
        for request_id in ids:
            reply = api.post("/predict", json=TRIP, headers={"X-Request-ID": request_id})
            assert reply.status_code == 200, reply.text
            body = reply.json()
            expected = route(request_id, weight)
            assert body.get("variant") == expected, (
                f"{request_id}: với ETA_CANARY_WEIGHT={weight}, route() chọn {expected}, pod trả {body.get('variant')}. "
                "Pod có thật sự chạy với cấu hình mới không (đổi ConfigMap không khởi động lại pod)?")
            canary += expected == "canary"
            version, eta = challenger if expected == "canary" else champion
            assert body.get("model_version") == version, f"nhánh {expected} phải báo version {version}: {body}"
            assert body.get("eta_s", 0) > 0 and body["eta_s"] == pytest.approx(eta, rel=ETA_REL), (
                f"nhánh {expected} báo {version} nhưng eta_s {body.get('eta_s')} không phải của model {version} ({eta:.3f})")
    low, high = split_bounds(weight, n)
    assert low <= canary <= high, (
        f"ETA_CANARY_WEIGHT={weight}: {canary}/{n} request vào canary, cần trong [{low}, {high}]; route() phải chia theo trọng số")


def split_bounds(weight: float, n: int) -> tuple[int, int]:
    """Khoảng chấp nhận số request canary trên `n` id cố định; rộng để mọi cách băm sha256 hợp lý đều qua."""
    if weight <= 0:
        return 0, 0
    return max(1, int(0.4 * weight * n)), min(n - 1, int(1.6 * weight * n) + 2)


def test_m12_manifests_contract(project):
    manifest = require_file("k8s", "eta.yaml")
    require_file("k8s", "Dockerfile.model")
    values = {key: f"value-{key.lower()}" for key in SERVE_VARS} | {"ETA_CANARY_WEIGHT": "0", "ETA_ADMIN_TOKEN": "tok-m12",
                                                                   "ETA_PRIORITY_CLASS": ""}
    docs = documents(render(manifest, **values))
    raw = manifest.read_text(encoding="utf-8")
    missing = [key for key in SERVE_VARS if f"${{{key}}}" not in raw and f"${key}" not in raw]
    assert not missing, f"k8s/eta.yaml phải dùng mọi biến release, còn thiếu {missing}"
    assert all(not (d.get("metadata") or {}).get("namespace") for d in docs), "không ghi cứng namespace: test apply vào namespace tạm"
    services = [d for d in docs if d.get("kind") == "InferenceService" and d["metadata"].get("name") == ISVC]
    assert services, f"cần InferenceService tên `{ISVC}`"
    isvc = services[0]
    annotations = isvc["metadata"].get("annotations") or {}
    predictor = isvc["spec"]["predictor"]
    assert annotations.get("serving.kserve.io/deploymentMode") in ("RawDeployment", "Standard"), \
        "đặt annotation serving.kserve.io/deploymentMode: RawDeployment (cluster không có Knative)"
    fixed = predictor.get("minReplicas") is not None and predictor.get("minReplicas") == predictor.get("maxReplicas")
    assert annotations.get("serving.kserve.io/autoscalerClass") in ("none", "external") or fixed, \
        "cluster không có metrics-server: autoscalerClass none (external từ M14) hoặc minReplicas == maxReplicas"
    containers = predictor.get("containers") or []
    assert len(containers) == 1, "predictor custom: đúng một container (image Dockerfile.serve)"
    main = containers[0]
    assert main.get("image") == values["ETA_SERVE_IMAGE"], "container chính dùng ${ETA_SERVE_IMAGE}"
    ports = [p.get("containerPort") for p in main.get("ports") or []]
    assert ports == [8000], f"container chính khai đúng một containerPort 8000 (Service :80 trỏ vào đó), có {ports}"
    assert predictor.get("automountServiceAccountToken") is False, \
        "predictor không cần gọi API Kubernetes: automountServiceAccountToken: false"
    assert (main.get("readinessProbe") or {}).get("httpGet", {}).get("path") == "/readyz", "readinessProbe gọi /readyz"
    assert (main.get("livenessProbe") or {}).get("httpGet", {}).get("path") == "/healthz", "livenessProbe gọi /healthz"
    resources = main.get("resources") or {}
    for part in ("requests", "limits"):
        assert {"cpu", "memory"} <= set(resources.get(part) or {}), f"container chính cần resources.{part} cpu và memory"
    pods = [main, *(predictor.get("initContainers") or [])]
    assert all(c.get("imagePullPolicy") in ("IfNotPresent", "Never") for c in pods), \
        "image nạp bằng kind_load: imagePullPolicy IfNotPresent (hoặc Never) cho mọi container"
    holders = [d for d in docs if "tok-m12" in json.dumps(d)]
    assert holders and all(d.get("kind") == "Secret" for d in holders), \
        "ETA_ADMIN_TOKEN chỉ nằm trong Secret, container đọc qua secretRef/secretKeyRef"


def test_m12_isvc_serves_champion(project, images, models):
    manifest = require_file("k8s", "eta.yaml")
    require_file("k8s", "Dockerfile.model")
    require_file("Dockerfile.serve")
    mlopskit.require_kind()
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    model, eta = models()["a"]
    version = f"v-{uuid.uuid4().hex[:6]}"
    token = uuid.uuid4().hex
    image = images.model("a", model)
    with mlopskit.k8s_namespace() as ns:
        deploy(ns, manifest, release_values(images, (image, version), (image, version), 0.0, token))
        serving(ns, version, version, 0.0)
        with mlopskit.port_forward(ns, SERVICE, 80) as port, httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as api:
            assert api.get("/healthz").status_code == 200
            reply = api.post("/predict", json=TRIP)
            assert reply.status_code == 200, reply.text
            body = reply.json()
            assert body.get("model_version") == version, f"Ready chưa đủ: /predict phải báo version {version}, nhận {body}"
            assert body.get("eta_s", 0) > 0 and body["eta_s"] == pytest.approx(eta, rel=ETA_REL), \
                f"eta_s {body.get('eta_s')} không phải của model {version} ({eta:.3f})"
            assert api.post("/admin/reload").status_code == 403, "Secret ETA_ADMIN_TOKEN phải tới được container"
            reloaded = api.post("/admin/reload", headers={"X-Admin-Token": token})
            assert reloaded.status_code == 200 and reloaded.json().get("champion") == version, reloaded.text


def test_m12_canary_rollout_and_rollback(project, images, models):
    manifest = require_file("k8s", "eta.yaml")
    require_file("k8s", "Dockerfile.model")
    require_file("Dockerfile.serve")
    mlopskit.require_kind()
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    built = models()
    run = uuid.uuid4().hex[:6]
    v1, v2 = f"v1-{run}", f"v2-{run}"
    image1, image2 = images.model("a", built["a"][0]), images.model("b", built["b"][0])
    token = uuid.uuid4().hex
    old, new = (v1, built["a"][1]), (v2, built["b"][1])
    releases = [((image1, v1), (image1, v1), 0.0), ((image1, v1), (image2, v2), 0.25),
                ((image1, v1), (image2, v2), 0.5), ((image1, v1), (image1, v1), 0.0)]
    with mlopskit.k8s_namespace() as ns:
        for champion, challenger, weight in releases:
            deploy(ns, manifest, release_values(images, champion, challenger, weight, token))
            serving(ns, champion[1], challenger[1], weight)
            check_split(ns, built["route"], weight, old, new if challenger[1] == v2 else old)


def submit(ns: str, workflow, image: str, month: str, champion_metrics: str) -> str:
    docs = documents(render(workflow, ETA_TRAIN_IMAGE=image))
    flows = [d for d in docs if d.get("kind") == "Workflow"]
    assert len(flows) == 1, "argo/train-workflow.yaml chứa đúng một Workflow"
    flow = flows[0]
    assert flow["metadata"].get("generateName") and not flow["metadata"].get("namespace"), \
        "Workflow dùng metadata.generateName, không ghi cứng namespace"
    params = {p.get("name"): p for p in (flow.get("spec", {}).get("arguments", {}).get("parameters") or [])}
    missing = [name for name in ("month", "champion-metrics") if name not in params]
    assert not missing, f"spec.arguments.parameters thiếu {missing}"
    params["month"]["value"] = month
    params["champion-metrics"]["value"] = champion_metrics
    created = mlopskit.kubectl("create", "-f", "-", "-o", "jsonpath={.metadata.name}", namespace=ns,
                               input=yaml.safe_dump(flow, allow_unicode=True))
    assert created.returncode == 0, f"kubectl create Workflow lỗi: {created.stderr[-2000:]}"
    return created.stdout.strip()


def finished(ns: str, name: str, expect: str) -> dict:
    """Chờ Workflow vào phase `expect`; rơi vào phase kết thúc khác thì fail ngay kèm describe, log, events."""
    other = tuple(p for p in ("Succeeded", "Failed", "Error") if p != expect)
    mlopskit.wait_for("workflow", name, f"jsonpath={{.status.phase}}={expect}", ns, WORKFLOW_TIMEOUT, fail_on=other)
    return json.loads(mlopskit.kubectl("get", "workflow", name, "-o", "json", namespace=ns).stdout or "{}").get("status", {})


def summary(status: dict) -> str:
    nodes = status.get("nodes", {}).values()
    return f"{status.get('phase')} {status.get('message') or ''} " + "; ".join(
        f"{n['displayName']}={n.get('phase')} {n.get('message') or ''}".strip() for n in nodes if n.get("type") != "DAG")


def steps(status: dict) -> dict:
    """Node Pod theo tên bước; bước có retryStrategy tên `train(0)`, `train(1)`: lấy lần chạy sau cùng."""
    found = {}
    pods = [n for n in status.get("nodes", {}).values() if n.get("type") == "Pod"]
    for node in sorted(pods, key=lambda n: n.get("startedAt") or ""):
        found[re.sub(r"\(\d+\)$", "", node["displayName"])] = node
    return found


def month_data(ns: str, folder, frame: pd.DataFrame) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"yellow_tripdata_{MONTH}.parquet"
    frame.to_parquet(path, index=False)
    made = mlopskit.kubectl("create", "configmap", DATA_CONFIGMAP, f"--from-file={path}", namespace=ns)
    assert made.returncode == 0, made.stderr


def test_m12_workflow_trains(project, images, tmp_path):
    workflow = require_file("argo", "train-workflow.yaml")
    require_file("Dockerfile.train")
    mlopskit.require_kind()
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    image = images.train()
    with mlopskit.k8s_namespace() as ns:
        month_data(ns, tmp_path, synthetic_month(1_500, month=MONTH, seed=5))
        name = submit(ns, workflow, image, MONTH, "{}")
        status = finished(ns, name, "Succeeded")
        nodes = steps(status)
        assert status.get("phase") == "Succeeded", f"Workflow phải Succeeded: {summary(status)}"
        assert set(STEPS) <= set(nodes), f"cần ba bước Pod {STEPS}, có {sorted(nodes)}"
        assert all(nodes[s]["phase"] == "Succeeded" for s in STEPS)
        for before, after in zip(STEPS, STEPS[1:]):
            assert nodes[before]["finishedAt"] <= nodes[after]["startedAt"], f"{after} phải chạy sau khi {before} xong"
        artifacts = {a["name"] for a in nodes["train"].get("outputs", {}).get("artifacts", [])}
        assert {"model", "metrics"} <= artifacts, f"bước train phải xuất artifact model và metrics, có {sorted(artifacts)}"
        inputs = {a["name"] for a in nodes["gate"].get("inputs", {}).get("artifacts", [])}
        assert "metrics" in inputs, "bước gate nhận artifact metrics của train"


def test_m12_gate_rejects_worse_model(project, images, tmp_path):
    workflow = require_file("argo", "train-workflow.yaml")
    require_file("Dockerfile.train")
    mlopskit.require_kind()
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    image = images.train()
    with mlopskit.k8s_namespace() as ns:
        month_data(ns, tmp_path, synthetic_month(1_500, month=MONTH, seed=5))
        name = submit(ns, workflow, image, MONTH, json.dumps({"mae": 1.0, "p90_abs_err": 2.0, "mae_airport": 1.0}))
        status = finished(ns, name, "Failed")
        nodes = steps(status)
        assert status.get("phase") == "Failed", f"champion tốt hơn hẳn thì Workflow phải Failed: {summary(status)}"
        assert nodes.get("validate", {}).get("phase") == "Succeeded" and nodes.get("train", {}).get("phase") == "Succeeded"
        gate = nodes.get("gate", {})
        assert gate.get("phase") == "Failed", f"Workflow phải dừng ở bước gate, các bước: { {k: v['phase'] for k, v in nodes.items()} }"
        assert str(gate.get("outputs", {}).get("exitCode")) == "3", f"gate từ chối thoát mã 3 (EXIT_REJECTED): {gate.get('message')}"


def test_m12_bad_month_stops_at_validate(project, images, tmp_path):
    workflow = require_file("argo", "train-workflow.yaml")
    require_file("Dockerfile.train")
    mlopskit.require_kind()
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    image = images.train()
    frame = synthetic_month(1_500, month=MONTH, seed=6)
    broken = frame.index[::10]
    frame.loc[broken, "tpep_dropoff_datetime"] = frame.loc[broken, "tpep_pickup_datetime"] - pd.Timedelta(minutes=5)
    with mlopskit.k8s_namespace() as ns:
        month_data(ns, tmp_path, frame)
        name = submit(ns, workflow, image, MONTH, "{}")
        status = finished(ns, name, "Failed")
        nodes = steps(status)
        assert status.get("phase") == "Failed", f"10% chuyến có thời lượng âm: validate phải chặn: {summary(status)}"
        assert nodes.get("validate", {}).get("phase") == "Failed", f"phải dừng ở validate: { {k: v['phase'] for k, v in nodes.items()} }"
        assert "train" not in nodes, "train không được chạy khi validate trượt"
