import json
import subprocess
import threading
import time

import pytest

from testkit import KUBE_IMAGES, Exercise, KubeLab

pytestmark = pytest.mark.kube_nodes

ex = Exercise(__file__)
INCIDENT = ex.fixtures / "incident"
DRAINED = "devops-lab-worker"
POOL = "devops-lab-worker2"
POOL_TAINT = {"key": "olist.io/pool", "value": "frontend", "effect": "NoSchedule"}
SELECTOR = "app.kubernetes.io/name=storefront"


def get_json(lab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def pods(lab) -> list[dict]:
    found = get_json(lab, "pods", "-l", SELECTOR) or {"items": []}
    return [p for p in found["items"] if not p["metadata"].get("deletionTimestamp")]


def placement(lab) -> dict:
    spread = {}
    for pod in pods(lab):
        node = pod["spec"].get("nodeName") or "Pending"
        spread[node] = spread.get(node, 0) + 1
    return spread


def scheduling_events(lab) -> str:
    events = get_json(lab, "events", "--field-selector", "reason=FailedScheduling") or {"items": []}
    return "\n".join(e.get("message", "") for e in events["items"])


def apply(lab, path):
    try:
        return lab.apply_learner(path, check=False)
    except pytest.fail.Exception as error:
        return subprocess.CompletedProcess([], 1, "", str(error))


def drain_watched(lab) -> tuple[subprocess.CompletedProcess, int]:
    lowest = [99]
    done = threading.Event()

    def watch():
        while not done.is_set():
            deployment = get_json(lab, "deployment", "storefront") or {}
            lowest[0] = min(lowest[0], (deployment.get("status") or {}).get("availableReplicas") or 0)
            time.sleep(1)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        result = lab.node_action({"action": "drain", "node": DRAINED}, check=False)
    finally:
        done.set()
        watcher.join(10)
    return result, lowest[0]


@pytest.fixture(scope="module")
def runs():
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["nginx"])
    state = {}
    with KubeLab() as lab:
        lab.node_action({"action": "taint", "node": POOL, "taint": POOL_TAINT})
        apply(lab, INCIDENT)
        time.sleep(30)
        state["incident_spread"] = placement(lab)
        state["incident_events"] = scheduling_events(lab)
        state["incident_drain"], _ = drain_watched(lab)
    with KubeLab() as lab:
        lab.node_action({"action": "taint", "node": POOL, "taint": POOL_TAINT})
        state["applied"] = apply(lab, ex.path("k8s"))
        state["rollout"] = lab.kubectl("rollout", "status", "deployment/storefront", "--timeout=120s", check=False, timeout=150)
        state["spread"] = placement(lab)
        state["deployment"] = get_json(lab, "deployment", "storefront")
        time.sleep(3)
        state["pdb"] = get_json(lab, "pdb")
        if state["rollout"].returncode == 0:
            state["drain"], state["lowest"] = drain_watched(lab)
            state["after_rollout"] = lab.kubectl("rollout", "status", "deployment/storefront", "--timeout=120s", check=False,
                                                 timeout=150)
            state["after_spread"] = placement(lab)
    yield state


def test_rolls_out_on_both_workers(runs):
    assert runs["applied"].returncode == 0, runs["applied"].stderr[-1500:]
    assert runs["rollout"].returncode == 0, f"storefront chưa đủ 4 pod: {runs['spread']}\n{runs['rollout'].stdout[-300:]}"
    assert runs["spread"].get(DRAINED, 0) >= 1 and runs["spread"].get(POOL, 0) >= 1, \
        f"4 pod phải trải trên cả hai worker (maxSkew 1): {runs['spread']}"


def test_design_kept(runs):
    spec = runs["deployment"]["spec"]
    assert spec["replicas"] == 4
    pod = spec["template"]["spec"]
    constraints = pod.get("topologySpreadConstraints") or []
    assert any(c.get("topologyKey") == "kubernetes.io/hostname" and c.get("maxSkew") == 1
               and c.get("whenUnsatisfiable") == "DoNotSchedule" for c in constraints), \
        "Giữ ràng buộc trải đều maxSkew 1 theo hostname, DoNotSchedule"
    for toleration in pod.get("tolerations") or []:
        assert toleration.get("key"), "Không dung thứ mọi taint (toleration không key) vì như vậy bỏ qua cả cordon"


def test_pdb_allows_exactly_one_disruption(runs):
    items = (runs["pdb"] or {}).get("items") or []
    budgets = [p for p in items if (p["spec"].get("selector") or {}).get("matchLabels") == {"app.kubernetes.io/name": "storefront"}]
    assert budgets, "Cần PodDisruptionBudget chọn app.kubernetes.io/name: storefront"
    status = budgets[0].get("status") or {}
    assert status.get("disruptionsAllowed") == 1, f"Khi đủ 4 pod, PDB cho phép đúng 1 pod bị evict cùng lúc: {status}"


def test_drain_completes_without_losing_capacity(runs):
    assert "drain" in runs, "Chưa rollout được nên chưa drain"
    assert runs["drain"].returncode == 0, f"kubectl drain {DRAINED} không xong:\n{runs['drain'].stderr[-800:]}"
    assert runs["lowest"] >= 3, f"Trong lúc drain số pod available xuống {runs['lowest']} (cần ≥ 3)"
    assert runs["after_rollout"].returncode == 0, f"Sau drain storefront không về đủ 4 pod: {runs['after_spread']}"
    assert runs["after_spread"] == {POOL: 4}, f"Sau drain cả 4 pod nằm trên {POOL}: {runs['after_spread']}"


def test_incident_reproduces_symptoms(runs):
    assert runs["incident_spread"].get("Pending", 0) >= 1, f"Bản lúc sự cố phải có pod Pending: {runs['incident_spread']}"
    events = runs["incident_events"]
    assert "untolerated taint {olist.io/pool: frontend}" in events and "topology spread" in events, events[-800:]
    drain = runs["incident_drain"]
    assert drain.returncode != 0 and "disruption budget" in drain.stderr, drain.stderr[-800:]
