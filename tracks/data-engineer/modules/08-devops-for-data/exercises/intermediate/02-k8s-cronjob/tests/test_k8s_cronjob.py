import yaml

from testkit import Exercise

ex = Exercise(__file__)


def docs():
    items = [d for d in yaml.safe_load_all(ex.read("k8s.yaml")) if d]
    return {d["kind"]: d for d in items}, items


def pod_spec():
    cron = docs()[0]["CronJob"]
    return cron["spec"]["jobTemplate"]["spec"]["template"]["spec"]


def container():
    containers = pod_spec()["containers"]
    assert len(containers) == 1
    return containers[0]


def test_three_documents_same_namespace():
    by_kind, items = docs()
    assert len(items) == 3
    assert set(by_kind) == {"ConfigMap", "Secret", "CronJob"}
    assert all(d["metadata"].get("namespace") == "data" for d in items)


def test_configmap_values_are_strings():
    cm = docs()[0]["ConfigMap"]
    data = cm["data"]
    assert data.get("TARGET_SCHEMA") == "staging"
    assert data.get("BATCH_SIZE") == "5000"
    assert all(isinstance(v, str) for v in data.values()), "Giá trị ConfigMap phải là chuỗi"


def test_secret_string_data():
    secret = docs()[0]["Secret"]
    assert secret.get("type") == "Opaque"
    assert (secret.get("stringData") or {}).get("DB_PASSWORD"), "Cần stringData.DB_PASSWORD"


def test_cronjob_schedule_and_policy():
    cron = docs()[0]["CronJob"]
    assert cron["apiVersion"] == "batch/v1"
    assert cron["spec"]["schedule"] == "0 * * * *"
    assert cron["spec"].get("concurrencyPolicy") == "Forbid"
    backoff = cron["spec"]["jobTemplate"]["spec"].get("backoffLimit")
    assert isinstance(backoff, int) and 1 <= backoff <= 5


def test_pod_restart_and_non_root():
    spec = pod_spec()
    assert spec.get("restartPolicy") == "OnFailure"
    pod_ctx = spec.get("securityContext") or {}
    ctr_ctx = container().get("securityContext") or {}
    assert pod_ctx.get("runAsNonRoot") is True or ctr_ctx.get("runAsNonRoot") is True


def test_image_pinned():
    image = container()["image"]
    name = image.split("@")[0]
    tag = name.rsplit(":", 1)[1] if ":" in name.split("/")[-1] else None
    assert ("@sha256:" in image) or (tag and tag != "latest"), f"Image {image} chưa pin tag"


def test_env_from_matches_names():
    by_kind, _ = docs()
    refs = container().get("envFrom") or []
    cm_refs = [r["configMapRef"]["name"] for r in refs if "configMapRef" in r]
    secret_refs = [r["secretRef"]["name"] for r in refs if "secretRef" in r]
    assert by_kind["ConfigMap"]["metadata"]["name"] in cm_refs
    assert by_kind["Secret"]["metadata"]["name"] in secret_refs


def test_resources():
    res = container().get("resources") or {}
    for kind in ("requests", "limits"):
        assert {"cpu", "memory"} <= set((res.get(kind) or {}).keys()), f"Thiếu {kind} cpu/memory"
