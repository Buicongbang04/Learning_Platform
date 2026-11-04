"""M14: ETA chịu tải trên K8s: KEDA autoscale theo metric của API, retrain qua Kueue, quota tách serving và training.

Đề ở capstone/milestones/m14-k8s-load.md. Mỗi test cluster tạo hai namespace tạm (serving, training) và tài nguyên
cluster-scoped có hậu tố run id (`mlopskit.cluster_scoped`), xoá khi xong kể cả khi fail.
"""

import calendar
import json
import math
import re
import string
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path

import httpx
import joblib
import pytest
import yaml
from etakit import need, require_file, synthetic_month

import mlopskit
import testkit

SERVE_VARS = ("ETA_SERVE_IMAGE", "ETA_CHAMPION_IMAGE", "ETA_CHAMPION_VERSION", "ETA_CHALLENGER_IMAGE",
              "ETA_CHALLENGER_VERSION", "ETA_CANARY_WEIGHT", "ETA_ADMIN_TOKEN", "ETA_PRIORITY_CLASS")
FILES = {"cluster.yaml": ("ETA_RUN",), "serving.yaml": ("ETA_NAMESPACE",), "training.yaml": ("ETA_RUN",),
         "retrain-job.yaml": ("ETA_RUN", "ETA_TRAIN_IMAGE", "ETA_MONTH")}
KINDS = {"cluster.yaml": {"PriorityClass", "ResourceFlavor", "ClusterQueue", "Cohort", "WorkloadPriorityClass"},
         "serving.yaml": {"ResourceQuota", "LimitRange", "ScaledObject"},
         "training.yaml": {"ResourceQuota", "LimitRange", "LocalQueue"},
         "retrain-job.yaml": {"Job"}}
ISVC = "eta"
DEPLOYMENT = "eta-predictor"
SERVICE = "eta-predictor"
NODE_PORT = "eta-load-m14"
SCALED_OBJECT = "eta"
QUEUE = "eta-retrain"
QUEUE_LABEL = "kueue.x-k8s.io/queue-name"
SERVING_CLASS = "eta-serving-{run}"
TRAINING_CLASS = "eta-training-{run}"
CLUSTER_QUEUE = "eta-training-{run}"
DATA_CONFIGMAP = "eta-train-data"
MONTH = "2019-03"
RUN_PLACEHOLDER = mlopskit.RUN_TOKEN
MIN_REPLICAS = (1, 2)
MAX_REPLICAS = (3, 6)
PEAK_REPLICAS = 3
FALLBACK_PEAK = 2
STAIRS = (50, 75, 100, 125, 150, 175, 200, 250, 300)
STAIR_S = 5
STAIR_WARMUP_S = 3
LOAD_FACTOR = 2.2
RATE_RANGE = (150, 400)
SETTLE_S = 10
WARM_S = 60
STEADY_S = 20
P95_MS = 300
MAX_FAILED = 0.01
ROLLOUT_TIMEOUT = 240
JOB_TIMEOUT = 300
SURGE = 1
ADDON_PRIORITY = 1_000_000
ADDON_NAMESPACES = ("kserve", "keda", "kueue-system", "cert-manager", "argo")

LOAD_SCRIPT = """
import http from "k6/http";
import { check } from "k6";

const ZONES = [48, 79, 132, 138, 161, 162, 230, 236, 237];
const LOAD = { executor: "constant-arrival-rate", rate: %(rate)d, timeUnit: "1s", preAllocatedVUs: 100, maxVUs: 900 };

export const options = {
  scenarios: {
    warm: Object.assign({}, LOAD, { duration: "%(warm)ds" }),
    steady: Object.assign({}, LOAD, { duration: "%(steady)ds", startTime: "%(warm)ds" }),
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "p(99)", "max"],
  thresholds: {
    "http_req_duration{scenario:steady}": ["p(95)<%(p95)d"],
    "http_req_failed{scenario:steady}": ["rate<%(failed)s"],
    "http_reqs{scenario:steady}": ["count>0"],
  },
};

export default function () {
  const body = JSON.stringify({
    PULocationID: ZONES[__ITER %% ZONES.length],
    DOLocationID: ZONES[(__ITER * 7) %% ZONES.length],
    pickup_datetime: "2019-03-12T08:15:00",
    trip_distance: 1 + (__ITER %% 80) / 10,
  });
  const res = http.post(`${__ENV.TARGET}/predict`, body, { headers: { "Content-Type": "application/json" } });
  check(res, { "status 200": (r) => r.status === 200 });
}
"""

STAIR_SCRIPT = """
import http from "k6/http";

const ZONES = [48, 79, 132, 138, 161, 162, 230, 236, 237];
const STAIRS = %(stairs)s;
const scenarios = {};
const thresholds = {};
scenarios.warmup = { executor: "constant-arrival-rate", rate: 20, timeUnit: "1s", duration: "%(warmup)ds",
                     preAllocatedVUs: 10, maxVUs: 50 };
STAIRS.forEach((rate, i) => {
  scenarios[`r${rate}`] = { executor: "constant-arrival-rate", rate: rate, timeUnit: "1s", duration: "%(step)ds",
                            startTime: `${%(warmup)d + i * %(step)d}s`, preAllocatedVUs: 50, maxVUs: 600,
                            gracefulStop: "2s" };
  thresholds[`http_req_duration{scenario:r${rate}}`] = [{ threshold: "p(95)<%(p95)d", abortOnFail: true, delayAbortEval: "3s" }];
  thresholds[`http_req_failed{scenario:r${rate}}`] = [{ threshold: "rate<%(failed)s", abortOnFail: true, delayAbortEval: "3s" }];
  thresholds[`http_reqs{scenario:r${rate}}`] = ["count>0"];
});

export const options = { scenarios: scenarios, thresholds: thresholds,
                         summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "p(99)", "max"] };

export default function () {
  const body = JSON.stringify({
    PULocationID: ZONES[__ITER %% ZONES.length],
    DOLocationID: ZONES[(__ITER * 7) %% ZONES.length],
    pickup_datetime: "2019-03-12T08:15:00",
    trip_distance: 1 + (__ITER %% 80) / 10,
  });
  http.post(`${__ENV.TARGET}/predict`, body, { headers: { "Content-Type": "application/json" } });
}
"""

QUANTITY = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+))(?:([eE][+-]?\d+)|(Ki|Mi|Gi|Ti|Pi|Ei|n|u|m|k|M|G|T|P|E))?$")
BINARY = {"Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "Pi": 2**50, "Ei": 2**60}
DECIMAL = {"n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15, "E": 1e18}


def quantity(value) -> float:
    match = QUANTITY.match(str(value).strip())
    if not match:
        pytest.fail(f"{value!r} không phải quantity Kubernetes hợp lệ (vd. 500m, 256Mi, 1Gi, 2)", pytrace=False)
    number, exponent, suffix = match.groups()
    if exponent:
        return float(number + exponent)
    return float(number) * (BINARY.get(suffix) or DECIMAL.get(suffix) or 1)


def render(path: Path, **values: str) -> str:
    try:
        return string.Template(path.read_text(encoding="utf-8")).substitute(values)
    except KeyError as err:
        pytest.fail(f"{path.name} dùng biến {err} không có trong danh sách biến của tệp này: {sorted(values)}", pytrace=False)
    except ValueError as err:
        pytest.fail(f"{path.name}: placeholder sai cú pháp ({err}); chỉ dùng ký tự $ cho biến của đề", pytrace=False)


def documents(text: str, name: str) -> list[dict]:
    try:
        docs = [d for d in yaml.safe_load_all(text) if d]
    except yaml.YAMLError as err:
        pytest.fail(f"{name}: YAML không hợp lệ sau khi thay biến: {err}", pytrace=False)
    if not all(isinstance(d, dict) for d in docs):
        pytest.fail(f"{name}: mỗi document phải là một object Kubernetes", pytrace=False)
    return docs


def dump(docs: list[dict]) -> str:
    return yaml.safe_dump_all(docs, sort_keys=False)


def manifest(name: str, **values: str) -> list[dict]:
    path = require_file("k8s", name)
    raw = path.read_text(encoding="utf-8")
    missing = [v for v in FILES[name] if f"${{{v}}}" not in raw and f"${v}" not in raw]
    if missing:
        pytest.fail(f"k8s/{name} phải dùng biến {missing}", pytrace=False)
    docs = documents(render(path, **values), name)
    unknown = sorted({str(d.get("kind")) for d in docs} - KINDS[name])
    if unknown:
        pytest.fail(f"k8s/{name} chỉ chứa {sorted(KINDS[name])}, có thêm {unknown}", pytrace=False)
    if name != "cluster.yaml" and any("namespace" in (d.get("metadata") or {}) for d in docs):
        pytest.fail(f"k8s/{name}: không ghi metadata.namespace (test apply vào namespace tạm)", pytrace=False)
    return docs


def named(docs: list[dict], kind: str, name: str | None = None) -> list[dict]:
    return [d for d in docs if d.get("kind") == kind and (name is None or (d.get("metadata") or {}).get("name") == name)]


def one(docs: list[dict], kind: str, name: str | None = None, where: str = "") -> dict:
    found = named(docs, kind, name)
    if len(found) != 1:
        pytest.fail(f"{where}cần đúng một {kind}{' tên ' + name if name else ''}, có {len(found)}", pytrace=False)
    return found[0]


def predictor(docs: list[dict]) -> dict:
    isvc = one(docs, "InferenceService", ISVC, "k8s/eta.yaml: ")
    return (isvc.get("spec") or {}).get("predictor") or {}


def pod_resources(spec: dict) -> dict[str, float]:
    """Request/limit hiệu lực của pod: max(tổng container chính, init container lớn nhất), như scheduler và quota tính."""
    total = {}
    for part in ("requests", "limits"):
        for key in ("cpu", "memory"):
            main = sum(quantity(((c.get("resources") or {}).get(part) or {}).get(key, 0)) for c in spec.get("containers") or [])
            init = max([quantity(((c.get("resources") or {}).get(part) or {}).get(key, 0))
                        for c in spec.get("initContainers") or []] or [0])
            total[f"{part}.{key}"] = max(main, init)
    return total


def serve_values(**overrides: str) -> dict:
    values = {key: f"value-{key.lower()}" for key in SERVE_VARS}
    values.update({"ETA_CANARY_WEIGHT": "0", "ETA_ADMIN_TOKEN": "tok-m14", "ETA_PRIORITY_CLASS": "eta-serving-m14"})
    values.update(overrides)
    return values


def cluster_values(run: str) -> dict:
    return {"ETA_RUN": run}


def job_values(run: str, image: str = "eta-train:m14") -> dict:
    return {"ETA_RUN": run, "ETA_TRAIN_IMAGE": image, "ETA_MONTH": MONTH}


def priority_classes(docs: list[dict], run: str) -> tuple[dict, dict]:
    serving = one(docs, "PriorityClass", SERVING_CLASS.format(run=run), "k8s/cluster.yaml: ")
    training = one(docs, "PriorityClass", TRAINING_CLASS.format(run=run), "k8s/cluster.yaml: ")
    return serving, training


def cluster_queue_quota(cq: dict) -> dict[str, float]:
    quota = {}
    for group in (cq.get("spec") or {}).get("resourceGroups") or []:
        for flavor in group.get("flavors") or []:
            for resource in flavor.get("resources") or []:
                name = resource.get("name")
                quota[name] = quota.get(name, 0) + quantity(resource.get("nominalQuota", 0))
    return quota


def job_pod(job: dict) -> dict:
    return ((job.get("spec") or {}).get("template") or {}).get("spec") or {}


def hardening_problems(spec: dict, where: str) -> list[str]:
    """Luật bảo mật pod như module 13/14: non-root, seccomp RuntimeDefault, không leo quyền, bỏ mọi capability."""
    pod = spec.get("securityContext") or {}
    problems = []
    for container in [*(spec.get("initContainers") or []), *(spec.get("containers") or [])]:
        own = container.get("securityContext") or {}
        name = f"{where}/{container.get('name')}"
        if not (own.get("runAsNonRoot", pod.get("runAsNonRoot")) is True):
            problems.append(f"{name}: runAsNonRoot: true")
        seccomp = (own.get("seccompProfile") or pod.get("seccompProfile") or {}).get("type")
        if seccomp != "RuntimeDefault":
            problems.append(f"{name}: seccompProfile RuntimeDefault")
        if own.get("allowPrivilegeEscalation") is not False:
            problems.append(f"{name}: allowPrivilegeEscalation: false")
        if "ALL" not in ((own.get("capabilities") or {}).get("drop") or []):
            problems.append(f"{name}: capabilities.drop [ALL]")
    return problems


def test_m14_manifests_contract(project):
    run = "m14contract"
    eta = documents(render(require_file("k8s", "eta.yaml"), **serve_values()), "eta.yaml")
    raw_eta = require_file("k8s", "eta.yaml").read_text(encoding="utf-8")
    assert "${ETA_PRIORITY_CLASS}" in raw_eta or "$ETA_PRIORITY_CLASS" in raw_eta, \
        "k8s/eta.yaml cần biến ${ETA_PRIORITY_CLASS} cho priorityClassName của predictor"
    isvc = one(eta, "InferenceService", ISVC, "k8s/eta.yaml: ")
    spec = predictor(eta)
    annotations = (isvc.get("metadata") or {}).get("annotations") or {}
    assert annotations.get("serving.kserve.io/autoscalerClass") == "external", \
        "KEDA quản lý số replica: InferenceService cần annotation serving.kserve.io/autoscalerClass: external"
    assert spec.get("priorityClassName") == "eta-serving-m14", "predictor.priorityClassName phải là ${ETA_PRIORITY_CLASS}"
    problems = hardening_problems(spec, "predictor")
    assert not problems, f"pod predictor thiếu luật bảo mật: {problems}"

    cluster = manifest("cluster.yaml", **cluster_values(run))
    for doc in cluster:
        assert run in str((doc.get("metadata") or {}).get("name", "")), \
            f"k8s/cluster.yaml: tên {doc.get('kind')} phải chứa ${{ETA_RUN}} (cluster dùng chung, mỗi lần chạy một bộ)"
    serving_class, training_class = priority_classes(cluster, run)
    for doc in (serving_class, training_class):
        assert doc.get("globalDefault") is not True, "PriorityClass không được globalDefault (cluster dùng chung)"
        assert isinstance(doc.get("value"), int), "PriorityClass.value phải là số nguyên"
    assert ADDON_PRIORITY > serving_class["value"] > training_class["value"] > 0, \
        "giá trị ưu tiên phải theo thứ tự 1 000 000 (mlops-system của controller add-on) > serving > training > 0"
    assert training_class.get("preemptionPolicy") == "Never", "PriorityClass training phải có preemptionPolicy: Never"
    cq_quota = cluster_queue_quota(one(cluster, "ClusterQueue", CLUSTER_QUEUE.format(run=run), "k8s/cluster.yaml: "))
    assert {"cpu", "memory"} <= set(cq_quota), "ClusterQueue training cần nominalQuota cho cpu và memory"

    namespace = "mlops-ex-m14contract"
    serving = manifest("serving.yaml", ETA_NAMESPACE=namespace)
    scaled = one(serving, "ScaledObject", SCALED_OBJECT, "k8s/serving.yaml: ")
    so = scaled.get("spec") or {}
    target = so.get("scaleTargetRef") or {}
    assert target.get("name") == DEPLOYMENT and target.get("kind", "Deployment") == "Deployment", \
        f"ScaledObject phải trỏ Deployment {DEPLOYMENT} do KServe tạo"
    low, high = so.get("minReplicaCount", 0), so.get("maxReplicaCount", 100)
    assert MIN_REPLICAS[0] <= low <= MIN_REPLICAS[1], f"minReplicaCount phải trong {list(MIN_REPLICAS)} (API online không scale về 0)"
    assert MAX_REPLICAS[0] <= high <= MAX_REPLICAS[1], f"maxReplicaCount phải trong {list(MAX_REPLICAS)}"
    triggers = so.get("triggers") or []
    assert [t.get("type") for t in triggers] == ["metrics-api"], "cần đúng một trigger kiểu metrics-api"
    meta = triggers[0].get("metadata") or {}
    assert meta.get("format") == "prometheus", "trigger metrics-api đọc /metrics của API: format prometheus"
    url = httpx.URL(str(meta.get("url", "")))
    assert url.host in (f"{SERVICE}.{namespace}", f"{SERVICE}.{namespace}.svc", f"{SERVICE}.{namespace}.svc.cluster.local") \
        and url.path == "/metrics", f"url của trigger phải là /metrics của Service {SERVICE} trong ${{ETA_NAMESPACE}}"
    assert str(meta.get("valueLocation") or "").strip(), "trigger cần valueLocation (tên metric)"
    quota = one(serving, "ResourceQuota", None, "k8s/serving.yaml: ")
    hard = (quota.get("spec") or {}).get("hard") or {}
    assert quantity(hard.get("count/jobs.batch", 1)) == 0, "namespace serving không nhận Job: count/jobs.batch: \"0\""
    pod = pod_resources(spec)
    pods = high + SURGE
    for key in ("requests.cpu", "requests.memory", "limits.cpu", "limits.memory", "pods"):
        assert key in hard, f"ResourceQuota serving cần hard.{key}"
        need_value = pods if key == "pods" else pods * pod[key]
        assert quantity(hard[key]) >= need_value, \
            f"ResourceQuota serving: hard.{key} không đủ cho maxReplicaCount + {SURGE} pod (rolling update) của predictor"

    training = manifest("training.yaml", **cluster_values(run))
    local = one(training, "LocalQueue", QUEUE, "k8s/training.yaml: ")
    assert (local.get("spec") or {}).get("clusterQueue") == CLUSTER_QUEUE.format(run=run), \
        f"LocalQueue {QUEUE} phải trỏ ClusterQueue eta-training-${{ETA_RUN}}"
    training_hard = ((one(training, "ResourceQuota", None, "k8s/training.yaml: ").get("spec") or {}).get("hard") or {})
    for key in ("cpu", "memory"):
        assert quantity(training_hard.get(f"requests.{key}", 0)) >= cq_quota[key], \
            f"ResourceQuota training: hard.requests.{key} nhỏ hơn nominalQuota {key} của ClusterQueue"

    job = one(manifest("retrain-job.yaml", **job_values(run)), "Job", None, "k8s/retrain-job.yaml: ")
    assert job.get("apiVersion") == "batch/v1", "Job retrain là batch/v1 (Kueue của cluster chỉ quản lý batch/v1 Job)"
    assert ((job.get("metadata") or {}).get("labels") or {}).get(QUEUE_LABEL) == QUEUE, \
        f"Job cần nhãn {QUEUE_LABEL}: {QUEUE}"
    template = job_pod(job)
    assert template.get("priorityClassName") == TRAINING_CLASS.format(run=run), \
        "pod của Job dùng PriorityClass eta-training-${ETA_RUN}"
    assert template.get("automountServiceAccountToken") is False, "Job retrain không gọi API Kubernetes"
    assert template.get("restartPolicy") == "Never", "pod của Job retrain: restartPolicy: Never"
    containers = template.get("containers") or []
    assert containers and containers[0].get("image") == "eta-train:m14", "container retrain dùng ${ETA_TRAIN_IMAGE}"
    assert all(c.get("imagePullPolicy") in ("IfNotPresent", "Never") for c in containers), \
        "image nạp bằng kind_load: imagePullPolicy IfNotPresent"
    problems = hardening_problems(template, "retrain")
    assert not problems, f"pod retrain thiếu luật bảo mật: {problems}"
    usage = pod_resources(template)
    for key in ("cpu", "memory"):
        assert usage[f"requests.{key}"] > 0, f"container retrain cần resources.requests.{key}"
        assert usage[f"requests.{key}"] <= cq_quota[key], f"một Job retrain phải vừa nominalQuota {key} của ClusterQueue"
    assert any(2 * usage[f"requests.{k}"] > cq_quota[k] for k in ("cpu", "memory")), \
        "ClusterQueue training chỉ được đủ chỗ cho đúng một Job retrain chạy cùng lúc"


class Images:
    """Build image một lần cho cả module, chỉ khi test đầu tiên cần; xoá image trên máy khi module xong."""

    def __init__(self, project: Path, folder: Path):
        self.project = project
        self.folder = folder
        self.stack = ExitStack()
        self.cache: dict[str, str] = {}

    def _load(self, key: str, context: Path, dockerfile: str) -> str:
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

    def model(self, synthetic_trips) -> str:
        if "model" in self.cache:
            return self.cache["model"]
        dockerfile = require_file("k8s", "Dockerfile.model")
        features = need("features", "build_features")
        train = need("train", "train")
        model = train.train(*features.build_features(synthetic_trips), {"max_iter": 30, "random_state": 0})
        context = self.folder / "model"
        context.mkdir(parents=True, exist_ok=True)
        context.chmod(0o755)
        joblib.dump(model, context / "model.joblib")
        (context / "model.joblib").chmod(0o644)
        (context / "Dockerfile.model").write_bytes(dockerfile.read_bytes())
        return self._load("model", context, "Dockerfile.model")


@pytest.fixture(scope="module")
def images(project, tmp_path_factory):
    images = Images(project, tmp_path_factory.mktemp("m14-images"))
    with images.stack:
        yield images


def require_cluster() -> None:
    mlopskit.require_senior_addons()
    if not testkit.docker_ready():
        pytest.skip("Docker chưa sẵn sàng")
    values = {c["metadata"]["name"]: c.get("value", 0) for c in get_json("priorityclasses")["items"]}
    low = [f"{d['metadata']['namespace']}/{d['metadata']['name']}" for d in get_json("deployments", "-A")["items"]
           if d["metadata"]["namespace"] in ADDON_NAMESPACES
           and values.get(d["spec"]["template"]["spec"].get("priorityClassName"), 0) < ADDON_PRIORITY]
    if low:
        pytest.skip(f"controller add-on chưa có PriorityClass mlops-system ({low[:3]}): pod serving của bài có thể đẩy "
                    "chúng ra. Chạy: bash setup/mlops/kind/up.sh --senior")


def get_json(*args: str, namespace: str | None = None) -> dict:
    result = mlopskit.kubectl("get", *args, "-o", "json", namespace=namespace)
    if result.returncode != 0:
        pytest.fail(f"kubectl get {' '.join(args)} lỗi: {result.stderr[-500:]}", pytrace=False)
    return json.loads(result.stdout)


def run_id(names: list[str]) -> str:
    for name in names:
        match = re.fullmatch(r"priorityclass/eta-serving-([0-9a-f]{8})", name)
        if match:
            return match.group(1)
    pytest.fail(f"k8s/cluster.yaml cần PriorityClass eta-serving-${{ETA_RUN}}, có {names}", pytrace=False)


def apply_cluster(stack: ExitStack) -> str:
    require_file("k8s", "cluster.yaml")
    docs = manifest("cluster.yaml", **cluster_values(RUN_PLACEHOLDER))
    return run_id(stack.enter_context(mlopskit.cluster_scoped(dump(docs))))


def class_values(run: str) -> tuple[int, int]:
    serving, training = priority_classes(manifest("cluster.yaml", **cluster_values(run)), run)
    return serving["value"], training["value"]


def apply_serving_quota(ns: str) -> list[dict]:
    docs = manifest("serving.yaml", ETA_NAMESPACE=ns)
    mlopskit.apply_manifest(dump([d for d in docs if d.get("kind") != "ScaledObject"]), ns)
    return docs


def apply_training(ns: str, run: str, tmp_path: Path) -> None:
    mlopskit.apply_manifest(dump(manifest("training.yaml", **cluster_values(run))), ns)
    path = tmp_path / f"yellow_tripdata_{MONTH}.parquet"
    synthetic_month(1_500, month=MONTH, seed=14).to_parquet(path, index=False)
    made = mlopskit.kubectl("create", "configmap", DATA_CONFIGMAP, f"--from-file={path}", namespace=ns)
    assert made.returncode == 0, made.stderr


def retrain_job(run: str, image: str, name: str, queue: bool = True) -> dict:
    job = one(manifest("retrain-job.yaml", **job_values(run, image)), "Job", None, "k8s/retrain-job.yaml: ")
    job["metadata"]["name"] = name
    job["metadata"].pop("generateName", None)
    if not queue:
        (job["metadata"].get("labels") or {}).pop(QUEUE_LABEL, None)
    return job


def deploy_serving(ns: str, images: Images, synthetic_trips, run: str) -> None:
    model = images.model(synthetic_trips)
    version = f"m14-{uuid.uuid4().hex[:6]}"
    values = serve_values(ETA_SERVE_IMAGE=images.serve(), ETA_CHAMPION_IMAGE=model, ETA_CHAMPION_VERSION=version,
                          ETA_CHALLENGER_IMAGE=model, ETA_CHALLENGER_VERSION=version, ETA_ADMIN_TOKEN=uuid.uuid4().hex,
                          ETA_PRIORITY_CLASS=SERVING_CLASS.format(run=run))
    mlopskit.apply_manifest(render(require_file("k8s", "eta.yaml"), **values), ns)
    generation = mlopskit.kubectl("get", "inferenceservice", ISVC, "-o", "jsonpath={.metadata.generation}",
                                  namespace=ns).stdout.strip()
    if not generation:
        pytest.fail(f"k8s/eta.yaml phải tạo InferenceService tên `{ISVC}`", pytrace=False)
    mlopskit.wait_for("inferenceservice", ISVC, f"jsonpath={{.status.observedGeneration}}={generation}", ns, 120)
    rollout = mlopskit.kubectl("rollout", "status", f"deployment/{DEPLOYMENT}", f"--timeout={ROLLOUT_TIMEOUT}s",
                               namespace=ns, timeout=ROLLOUT_TIMEOUT + 30)
    if rollout.returncode != 0:
        events = mlopskit.kubectl("get", "events", "--sort-by=.lastTimestamp", namespace=ns).stdout
        pytest.fail(f"deployment/{DEPLOYMENT} không rollout xong sau {ROLLOUT_TIMEOUT} giây: {rollout.stderr[-500:]}\n"
                    f"--- events\n{events[-3000:]}", pytrace=False)
    mlopskit.wait_for("inferenceservice", ISVC, "Ready", ns, ROLLOUT_TIMEOUT)


def node_url(ns: str) -> str:
    node = mlopskit.kubectl("get", "nodes", "-o", "jsonpath={.items[0].metadata.name}").stdout.strip()
    port = get_json("service", NODE_PORT, namespace=ns)["spec"]["ports"][0]["nodePort"]
    return f"http://{node}:{port}"


def ready_endpoints(ns: str, service: str) -> int:
    result = mlopskit.kubectl("get", "endpointslices", "-l", f"kubernetes.io/service-name={service}", "-o", "json",
                              namespace=ns)
    if result.returncode != 0:
        return 0
    return sum(1 for s in json.loads(result.stdout)["items"] for e in s.get("endpoints") or []
               if (e.get("conditions") or {}).get("ready"))


def deployment_state(ns: str) -> tuple[int, int]:
    result = mlopskit.kubectl("get", "deployment", DEPLOYMENT, "-o", "json", namespace=ns)
    if result.returncode != 0:
        return 0, 0
    body = json.loads(result.stdout)
    return int((body.get("spec") or {}).get("replicas") or 0), int((body.get("status") or {}).get("readyReplicas") or 0)


def quota_events(ns: str) -> list[str]:
    events = get_json("events", namespace=ns)["items"]
    return [e.get("message", "") for e in events if "exceeded quota" in e.get("message", "")]


def metric_name(location: str) -> str:
    return re.split(r"[{\s]", location.strip(), maxsplit=1)[0]


def scrape(ns: str, target: str, port: int) -> str:
    with mlopskit.port_forward(ns, target, port) as local:
        reply = httpx.get(f"http://127.0.0.1:{local}/metrics", timeout=10)
    assert reply.status_code == 200, f"GET /metrics của {target} trả {reply.status_code}"
    return reply.text


def metric_type(text: str, name: str) -> str | None:
    match = re.search(rf"^# TYPE {re.escape(name)} (\w+)\s*$", text, re.M)
    return match.group(1) if match else None


def metric_value(text: str, name: str) -> float | None:
    values = [float(m.group(1)) for m in re.finditer(rf"^{re.escape(name)}(?:\{{[^}}]*\}})?\s+(\S+)\s*$", text, re.M)]
    return sum(values) if values else None


def predictor_pods(ns: str) -> list[str]:
    items = get_json("pods", "-l", f"serving.kserve.io/inferenceservice={ISVC}", namespace=ns)["items"]
    return [p["metadata"]["name"] for p in items
            if not p["metadata"].get("deletionTimestamp")
            and any(c.get("type") == "Ready" and c.get("status") == "True" for c in (p.get("status") or {}).get("conditions") or [])]


def pod_priorities(ns: str, selector: str) -> set:
    return {p["spec"].get("priority") for p in get_json("pods", "-l", selector, namespace=ns)["items"]}


def k6_summary(script: Path, target: str, timeout: int) -> dict:
    env = {"TARGET": target, "K6_NO_CONNECTION_REUSE": "true"}
    result = mlopskit.k6_run(script, env, network="kind", timeout=timeout)
    if not result.stdout:
        pytest.fail(f"k6 không xuất summary (rc={result.returncode}):\n{result.stderr[-2500:]}", pytrace=False)
    return json.loads(result.stdout)["metrics"]


def capacity(script: Path, target: str) -> tuple[int, list[str]]:
    """Bậc tải cao nhất (liên tục từ bậc đầu) mà một pod giữ được p95 ≤ P95_MS và lỗi < MAX_FAILED; 0 nếu bậc đầu đã trượt.

    k6 dừng ngay ở bậc trượt đầu tiên (`abortOnFail`), không đẩy tiếp tải vào pod đã bão hoà; bậc không chạy coi như trượt.
    """
    metrics = k6_summary(script, target, STAIR_WARMUP_S + len(STAIRS) * STAIR_S + 120)
    best, log = 0, []
    for rate in STAIRS:
        p95 = (metrics.get(f"http_req_duration{{scenario:r{rate}}}") or {}).get("p(95)", math.inf)
        failed = (metrics.get(f"http_req_failed{{scenario:r{rate}}}") or {}).get("value", 1)
        log.append(f"{rate} req/s: p95 {p95:.0f} ms, lỗi {failed:.1%}")
        if p95 > P95_MS or failed >= MAX_FAILED:
            break
        best = rate
    return best, log


def load_rate(measured: int) -> tuple[int, bool]:
    """(tải chấm, có đủ tải để đòi PEAK_REPLICAS không): 2,2 lần sức một pod, kẹp trong RATE_RANGE."""
    wanted = math.ceil(LOAD_FACTOR * max(measured, STAIRS[0]))
    rate = min(max(wanted, RATE_RANGE[0]), RATE_RANGE[1])
    return rate, wanted <= RATE_RANGE[1]


def test_m14_scales_under_load(project, images, synthetic_trips, tmp_path):
    for name in ("eta.yaml", "cluster.yaml", "serving.yaml", "training.yaml", "retrain-job.yaml", "Dockerfile.model"):
        require_file("k8s", name)
    require_cluster()
    stairs = tmp_path / "m14-stairs.js"
    stairs.write_text(STAIR_SCRIPT % {"stairs": json.dumps(list(STAIRS)), "step": STAIR_S, "warmup": STAIR_WARMUP_S,
                                      "p95": P95_MS, "failed": MAX_FAILED}, encoding="utf-8")
    with ExitStack() as stack:
        run = apply_cluster(stack)
        serving_value, training_value = class_values(run)
        serving_ns = stack.enter_context(mlopskit.k8s_namespace())
        training_ns = stack.enter_context(mlopskit.k8s_namespace())
        service = {"apiVersion": "v1", "kind": "Service", "metadata": {"name": NODE_PORT},
                   "spec": {"type": "NodePort", "selector": {"serving.kserve.io/inferenceservice": ISVC},
                            "ports": [{"port": 8000, "targetPort": 8000}]}}
        mlopskit.apply_manifest(dump([service]), serving_ns)
        serving_docs = apply_serving_quota(serving_ns)
        deploy_serving(serving_ns, images, synthetic_trips, run)
        target = node_url(serving_ns)
        wait_until(lambda: ready_endpoints(serving_ns, NODE_PORT) >= 1, 60, f"Service {NODE_PORT} chưa có endpoint Ready")
        measured, stair_log = capacity(stairs, target)
        rate, full = load_rate(measured)
        need_peak = PEAK_REPLICAS if full else FALLBACK_PEAK
        print(f"\nsức một pod C = {measured} req/s ({'; '.join(stair_log)}); tải chấm {rate} req/s, cần ít nhất "
              f"{need_peak} replica")
        script = tmp_path / "m14-load.js"
        script.write_text(LOAD_SCRIPT % {"rate": rate, "warm": WARM_S, "steady": STEADY_S, "p95": P95_MS,
                                         "failed": MAX_FAILED}, encoding="utf-8")

        apply_training(training_ns, run, tmp_path)
        mlopskit.apply_manifest(dump([retrain_job(run, images.train(), "eta-retrain-load")]), training_ns)

        scaled = [d for d in serving_docs if d.get("kind") == "ScaledObject"]
        mlopskit.apply_manifest(dump(scaled), serving_ns)
        mlopskit.wait_for("scaledobject", SCALED_OBJECT, "Ready", serving_ns, 120)
        trigger = scaled[0]["spec"]["triggers"][0].get("metadata") or {}
        name = metric_name(str(trigger.get("valueLocation", "")))
        threshold = float(trigger.get("targetValue", "nan"))
        exposed = scrape(serving_ns, f"svc/{SERVICE}", 80)
        assert metric_value(exposed, name) is not None, "valueLocation của trigger phải là một metric có trong /metrics của API"
        assert metric_type(exposed, name) == "gauge", \
            "metric của trigger phải là gauge (`# TYPE <tên> gauge` trong /metrics): counter chỉ tăng, HPA không bao giờ hạ"
        before, _ = deployment_state(serving_ns)

        samples: list[tuple[float, int, int]] = []
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(k6_summary, script, target, WARM_S + STEADY_S + 120)
            while not future.done():
                samples.append((time.monotonic() - started, *deployment_state(serving_ns)))
                time.sleep(2)
            metrics = future.result()

        time.sleep(SETTLE_S)
        idle = {pod: metric_value(scrape(serving_ns, f"pod/{pod}", 8000), name) for pod in predictor_pods(serving_ns)}
        wait_until(lambda: bool(pod_priorities(training_ns, "job-name=eta-retrain-load")), 120,
                   "Job retrain chạy song song với tải chưa có pod")

        steady = metrics.get("http_req_duration{scenario:steady}") or {}
        failed = (metrics.get("http_req_failed{scenario:steady}") or {}).get("value", 1)
        count = (metrics.get("http_reqs{scenario:steady}") or {}).get("count", 0)
        peak = max((s[1] for s in samples), default=0)
        ready = max((s[2] for s in samples), default=0)
        print(f"replica trước tải {before}, cao nhất {peak} (Ready {ready}); steady {count} request, "
              f"p95 {steady.get('p(95)', float('nan')):.1f} ms, lỗi {failed:.2%}; metric {SETTLE_S} giây sau tải: {idle}")
        print("t(s) replicas ready: " + ", ".join(f"{t:.0f}:{r}/{k}" for t, r, k in samples[::3]))
        blocked = quota_events(serving_ns)
        assert not blocked, f"ResourceQuota của namespace serving chặn pod khi autoscale: {blocked[:2]}"
        assert before <= MIN_REPLICAS[1], f"trước khi có tải đã có {before} replica"
        assert peak > before and peak >= need_peak and ready >= need_peak, \
            f"dưới tải {rate} req/s, Deployment {DEPLOYMENT} chỉ lên {peak} replica ({ready} Ready), cần ít nhất {need_peak}"
        assert idle and all(v is not None and v <= threshold for v in idle.values()), \
            f"{SETTLE_S} giây sau khi hết tải, metric của trigger trên từng pod phải về dưới targetValue ({threshold:g})"
        assert count > 0, "k6 không gửi request nào ở pha steady"
        assert failed < MAX_FAILED, f"pha steady có {failed:.2%} request lỗi"
        assert steady.get("p(95)", float("inf")) <= P95_MS, \
            f"p95 pha steady {steady.get('p(95)'):.0f} ms vượt {P95_MS} ms"
        assert pod_priorities(serving_ns, f"serving.kserve.io/inferenceservice={ISVC}") == {serving_value}, \
            "pod predictor phải chạy với PriorityClass eta-serving-${ETA_RUN}"
        assert pod_priorities(training_ns, "job-name=eta-retrain-load") == {training_value}, \
            "pod retrain phải chạy với PriorityClass eta-training-${ETA_RUN}"


def workloads(ns: str) -> dict[str, dict]:
    found = {}
    for item in get_json("workloads.kueue.x-k8s.io", namespace=ns)["items"]:
        for owner in item["metadata"].get("ownerReferences") or []:
            if owner.get("kind") == "Job":
                found[owner["name"]] = item
    return found


def condition(obj: dict, kind: str) -> dict:
    for item in (obj.get("status") or {}).get("conditions") or []:
        if item.get("type") == kind:
            return item
    return {}


def admitted(workload: dict | None) -> bool:
    return condition(workload or {}, "Admitted").get("status") == "True"


def job_status(ns: str, name: str) -> dict:
    return get_json("job", name, namespace=ns).get("status") or {}


def wait_until(predicate, timeout: float, what: str, interval: float = 1) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            pytest.fail(f"{what} sau {timeout:.0f} giây", pytrace=False)
        time.sleep(interval)


def stamp(value: str) -> float:
    return float(calendar.timegm(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ")))


def test_m14_retrain_queued_and_isolated(project, images, tmp_path):
    for name in ("cluster.yaml", "serving.yaml", "training.yaml", "retrain-job.yaml"):
        require_file("k8s", name)
    require_cluster()
    image = images.train()
    jobs = ("eta-retrain-1", "eta-retrain-2")
    with ExitStack() as stack:
        run = apply_cluster(stack)
        serving_value, training_value = class_values(run)
        serving_ns = stack.enter_context(mlopskit.k8s_namespace())
        training_ns = stack.enter_context(mlopskit.k8s_namespace())
        apply_serving_quota(serving_ns)
        apply_training(training_ns, run, tmp_path)

        stray = mlopskit.apply_manifest(dump([retrain_job(run, image, "eta-retrain-stray", queue=False)]), serving_ns,
                                        check=False)
        assert stray.returncode != 0 and "forbidden" in stray.stderr.lower(), \
            "namespace serving vẫn nhận một Job retrain tạo thẳng (không qua hàng đợi)"

        mlopskit.apply_manifest(dump([retrain_job(run, image, name) for name in jobs]), training_ns)
        wait_until(lambda: any(admitted(w) for w in workloads(training_ns).values()), 60,
                   "chưa Job retrain nào được Kueue admit")
        current = workloads(training_ns)
        assert set(jobs) <= set(current), "có Job retrain không đi qua Kueue (không có Workload)"
        running = [job for job in jobs if admitted(current[job])]
        assert len(running) == 1, f"hai Job retrain nộp cùng lúc: {len(running)} được admit, cần đúng một, Job kia chờ quota"
        first, second = running[0], next(job for job in jobs if job not in running)
        assert not get_json("pods", "-l", f"job-name={second}", namespace=training_ns)["items"], \
            f"Job {second} đang chờ quota mà đã có pod"

        def done(job: str) -> bool:
            blocked = quota_events(training_ns)
            if blocked:
                pytest.fail(f"ResourceQuota của namespace training chặn pod của Job đã được admit: {blocked[:2]}",
                            pytrace=False)
            status = job_status(training_ns, job)
            return bool(status.get("succeeded") or status.get("failed"))

        wait_until(lambda: all(done(job) for job in jobs), JOB_TIMEOUT, "hai Job retrain chưa chạy xong")
        for job in jobs:
            status = job_status(training_ns, job)
            if not status.get("succeeded"):
                logs = mlopskit.kubectl("logs", f"job/{job}", "--all-containers", "--tail=40", namespace=training_ns)
                pytest.fail(f"Job {job} không thành công: {status}\n{logs.stdout[-3000:]}{logs.stderr[-500:]}",
                            pytrace=False)
            logs = mlopskit.kubectl("logs", f"job/{job}", "--all-containers", namespace=training_ns).stdout
            assert '"mae"' in logs, f"Job {job} không in metric JSON của eta.cli train (có thật sự train không?)"
        finished_at = stamp(job_status(training_ns, first)["completionTime"])
        later = condition(workloads(training_ns)[second], "Admitted").get("lastTransitionTime")
        assert later and stamp(later) >= finished_at - 1, f"Job {second} được admit trước khi Job {first} chạy xong"
        for job, workload in workloads(training_ns).items():
            if job in jobs:
                assert (workload.get("spec") or {}).get("priority") == training_value < serving_value, \
                    f"Workload của {job} phải mang độ ưu tiên của PriorityClass eta-training-${{ETA_RUN}}"
