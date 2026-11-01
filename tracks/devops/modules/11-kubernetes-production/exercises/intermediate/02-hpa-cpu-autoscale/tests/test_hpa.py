import json
import subprocess
import time

import pytest

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
DEPS = ex.fixtures / "deps.yaml"
LOAD = ex.fixtures / "loadgen.yaml"
METRICS_WAIT = 150
SCALE_WAIT = 300


def get_json(lab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def cpu_utilization(hpa: dict):
    for metric in (hpa.get("status") or {}).get("currentMetrics") or []:
        if metric.get("type") == "Resource" and metric["resource"].get("name") == "cpu":
            return metric["resource"]["current"].get("averageUtilization")
    return None


def wait_hpa(lab, check, timeout: float):
    started = time.monotonic()
    seen = []
    while time.monotonic() - started < timeout:
        hpa = get_json(lab, "hpa", "api") or {}
        status = hpa.get("status") or {}
        seen.append((round(time.monotonic() - started), cpu_utilization(hpa), status.get("currentReplicas")))
        if check(hpa):
            return round(time.monotonic() - started), seen
        time.sleep(5)
    return None, seen


@pytest.fixture(scope="module")
def scaled():
    ex.require_cluster()
    ex.require_metrics()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab() as lab:
        lab.apply_learner(DEPS)
        for target in ("deployment/postgres", "deployment/redis"):
            lab.kubectl("rollout", "status", target, "--timeout=180s", timeout=200)
        try:
            applied = lab.apply_learner(ex.path("k8s"), check=False)
        except pytest.fail.Exception as error:
            applied = subprocess.CompletedProcess([], 1, "", str(error))
        state = {"applied": applied, "max": 0}
        if applied.returncode == 0:
            state["rollout"] = lab.kubectl("rollout", "status", "deployment/api", "--timeout=180s", check=False, timeout=200)
            state["metrics"], state["metrics_seen"] = wait_hpa(lab, lambda h: cpu_utilization(h) is not None, METRICS_WAIT)
        if state.get("metrics") is not None:
            state["idle"] = (get_json(lab, "hpa", "api") or {}).get("status", {}).get("currentReplicas")
            lab.apply_learner(LOAD)
            lab.kubectl("rollout", "status", "deployment/loadgen", "--timeout=120s")

            def up(hpa):
                current = (hpa.get("status") or {}).get("currentReplicas") or 0
                state["max"] = max(state["max"], current)
                return current >= 2

            state["up"], state["up_seen"] = wait_hpa(lab, up, SCALE_WAIT)
            if state["up"] is not None:
                wait_hpa(lab, lambda h: up(h) and False, 30)
            state["top"] = lab.kubectl("top", "pods", "-l", "app.kubernetes.io/name=api", check=False)
            lab.kubectl("delete", "deployment", "loadgen", "--wait=true", "--timeout=60s")
            if state["up"] is not None:
                state["down"], state["down_seen"] = wait_hpa(lab, lambda h: (h.get("status") or {}).get("currentReplicas") == 1,
                                                             SCALE_WAIT)
        yield lab, state


def test_manifests_apply(scaled):
    _, state = scaled
    assert state["applied"].returncode == 0, state["applied"].stderr[-1500:]
    assert state["rollout"].returncode == 0, state["rollout"].stdout[-500:] + state["rollout"].stderr[-500:]


def test_hpa_spec(scaled):
    lab, _ = scaled
    hpa = get_json(lab, "hpa", "api")
    assert hpa, "Cần HorizontalPodAutoscaler api"
    assert hpa["apiVersion"] == "autoscaling/v2"
    spec = hpa["spec"]
    assert spec["scaleTargetRef"] == {"apiVersion": "apps/v1", "kind": "Deployment", "name": "api"}, spec["scaleTargetRef"]
    assert (spec.get("minReplicas"), spec.get("maxReplicas")) == (1, 4), "minReplicas 1, maxReplicas 4"
    targets = [m["resource"]["target"] for m in spec.get("metrics") or [] if m.get("type") == "Resource"
               and m["resource"]["name"] == "cpu"]
    assert targets == [{"type": "Utilization", "averageUtilization": 60}], f"Một metric CPU Utilization 60%: {targets}"
    window = (((spec.get("behavior") or {}).get("scaleDown") or {}).get("stabilizationWindowSeconds"))
    assert window is not None and window <= 60, "behavior.scaleDown.stabilizationWindowSeconds tối đa 60 cho lab (mặc định 300)"


def test_api_requests_cpu(scaled):
    lab, _ = scaled
    deployment = get_json(lab, "deployment", "api")
    assert deployment, "Cần Deployment api"
    for container in deployment["spec"]["template"]["spec"]["containers"]:
        assert (container.get("resources") or {}).get("requests", {}).get("cpu"), \
            f"Container {container['name']} cần requests.cpu: HPA tính Utilization theo request"


def test_manifest_leaves_replicas_to_hpa():
    import yaml

    docs = [d for f in sorted(ex.path("k8s").glob("*.yaml")) for d in yaml.safe_load_all(f.read_text(encoding="utf-8")) if d]
    deployments = [d for d in docs if d.get("kind") == "Deployment" and d["metadata"]["name"] == "api"]
    assert deployments, "k8s/ cần Deployment api"
    assert "replicas" not in deployments[0]["spec"], \
        "Bỏ spec.replicas khỏi manifest khi HPA quản số replica, nếu không mỗi lần apply sẽ kéo replica về con số trong tệp"


def test_metrics_reach_hpa(scaled):
    _, state = scaled
    assert state.get("metrics") is not None, f"HPA chưa đọc được CPU sau {METRICS_WAIT}s: {state.get('metrics_seen', [])[-3:]}"
    assert state["idle"] == 1, f"Khi rảnh api chạy minReplicas (1), đang {state['idle']}"


def test_scales_up_under_load(scaled):
    _, state = scaled
    assert state.get("up") is not None, f"Có tải mà HPA không scale lên trong {SCALE_WAIT}s: {state.get('up_seen', [])[-4:]}"
    assert state["max"] <= 4, f"Vượt maxReplicas: {state['max']}"
    assert state["top"].returncode == 0 and "api-" in state["top"].stdout, state["top"].stderr


def test_scales_down_after_load(scaled):
    _, state = scaled
    assert state.get("down") is not None, f"Hết tải mà HPA không về 1 replica trong {SCALE_WAIT}s: {state.get('down_seen', [])[-4:]}"
