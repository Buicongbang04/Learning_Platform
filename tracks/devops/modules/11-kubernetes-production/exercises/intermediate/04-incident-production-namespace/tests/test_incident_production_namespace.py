import json
import subprocess
import time

import pytest
import yaml

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
PLATFORM = ex.fixtures / "platform.yaml"
INCIDENT = ex.fixtures / "incident" / "overlays" / "production"
WORKLOADS = ("api", "postgres", "redis", "pod-reporter")
READYZ = ("import json, urllib.request; r = urllib.request.urlopen('http://api:8000/readyz', timeout=5); "
          "print(r.status, json.dumps(json.load(r)))")


def get_json(lab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def apply(lab, path):
    try:
        return lab.apply_learner(path, check=False)
    except pytest.fail.Exception as error:
        return subprocess.CompletedProcess([], 1, "", str(error))


def failed_create(lab) -> str:
    events = get_json(lab, "events", "--field-selector", "reason=FailedCreate") or {"items": []}
    return "\n".join(f"{e['involvedObject']['name']}: {e.get('message', '')}" for e in events["items"])


def start(lab, path):
    lab.apply_learner(PLATFORM)
    applied = apply(lab, path)
    waited = None
    if applied.returncode == 0:
        waited = lab.kubectl("wait", "--for=condition=Available", *(f"deployment/{w}" for w in WORKLOADS), "--timeout=180s",
                             check=False, timeout=210)
    return applied, waited


@pytest.fixture(scope="module")
def production():
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab(pod_security="restricted") as lab:
        applied, waited = start(lab, ex.path("overlays/production"))
        state = {"applied": applied, "waited": waited, "events": failed_create(lab)}
        if waited is not None and waited.returncode == 0:
            deadline = time.monotonic() + 60
            logs = ""
            while time.monotonic() < deadline:
                logs = lab.kubectl("logs", "deployment/pod-reporter", "--tail=1", check=False).stdout
                last = json.loads(logs) if logs.startswith("{") else {}
                if "error" in last or last.get("ready", 0) >= 6:
                    break
                time.sleep(3)
            state["logs"] = logs
        yield lab, state


@pytest.fixture(scope="module")
def incident():
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab(pod_security="restricted") as lab:
        lab.apply_learner(PLATFORM)
        lab.apply_learner(INCIDENT)
        time.sleep(20)
        yield lab


def rendered(lab) -> list[dict]:
    return lab.manifests(ex.path("overlays/production"))


def test_overlay_applies(production):
    _, state = production
    assert state["applied"].returncode == 0, state["applied"].stderr[-1500:]


def test_all_workloads_available(production):
    _, state = production
    assert state["waited"] is not None and state["waited"].returncode == 0, \
        f"Chưa đủ Deployment Available sau 180 giây. FailedCreate:\n{state['events'][-1500:]}"


def test_api_capacity_and_measured_requests_kept(production):
    lab, _ = production
    api = get_json(lab, "deployment", "api")
    assert api, "Cần Deployment api"
    assert api["spec"]["replicas"] >= 3 and api["status"].get("readyReplicas") == api["spec"]["replicas"], \
        f"api cần ít nhất 3 replica, tất cả ready: {api['spec']['replicas']} / {api['status'].get('readyReplicas')}"
    container = next(c for c in api["spec"]["template"]["spec"]["containers"] if c["name"] == "api")
    assert container["resources"]["requests"] == {"cpu": "100m", "memory": "256Mi"}, "Giữ requests đo được từ staging"
    assert {"name": "LOG_LEVEL", "value": "WARNING"} in container.get("env", [])
    result = lab.kubectl("exec", "deployment/pod-reporter", "--", "python", "-c", READYZ, check=False)
    assert result.stdout.startswith("200"), result.stdout + result.stderr[-300:]


def test_platform_guardrails_untouched(production):
    lab, _ = production
    kinds = {d["kind"] for d in rendered(lab)}
    assert not kinds & {"ResourceQuota", "LimitRange", "Namespace"}, "Overlay không tạo hay đè ResourceQuota, LimitRange, Namespace"
    quota = get_json(lab, "resourcequota", "production")
    expected = yaml.safe_load(PLATFORM.read_text(encoding="utf-8").split("---")[0])["spec"]["hard"]
    assert quota and quota["spec"]["hard"] == expected, "ResourceQuota production của platform phải giữ nguyên"
    labels = get_json(lab, "namespace", lab.namespace)["metadata"]["labels"]
    assert labels.get("pod-security.kubernetes.io/enforce") == "restricted"


def test_secret_comes_from_generator(production):
    lab, _ = production
    api = get_json(lab, "deployment", "api")
    refs = [e["valueFrom"]["secretKeyRef"]["name"] for c in api["spec"]["template"]["spec"]["containers"]
            for e in c.get("env", []) if "secretKeyRef" in (e.get("valueFrom") or {})]
    assert refs and all(name.startswith("olist-db-") for name in refs), \
        f"api dùng Secret do secretGenerator sinh (tên có hậu tố hash): {refs}"


def test_pod_reporter_reads_pods(production):
    lab, state = production
    lines = [json.loads(line) for line in (state.get("logs") or "").splitlines() if line.startswith("{")]
    assert lines and "error" not in lines[-1] and lines[-1].get("ready", 0) >= 6, f"Log của pod-reporter: {state.get('logs')}"
    assert lab.can_i("list", "pods", serviceaccount="pod-reporter")
    assert not lab.can_i("get", "secrets", serviceaccount="pod-reporter"), "pod-reporter chỉ cần đọc pod"
    assert not lab.can_i("delete", "pods", serviceaccount="pod-reporter")


def test_incident_reproduces_symptoms(incident):
    lab = incident
    events = failed_create(lab)
    assert "api" in events and "maximum memory usage per Container is 512Mi" in events, events[-1000:]
    assert "pod-reporter" in events and 'violates PodSecurity "restricted:latest"' in events, events[-1000:]
    assert (get_json(lab, "deployment", "api") or {}).get("status", {}).get("readyReplicas") is None
    assert not lab.can_i("list", "pods", serviceaccount="pod-reporter"), "Bản lúc sự cố: pod-reporter không list được pod"
