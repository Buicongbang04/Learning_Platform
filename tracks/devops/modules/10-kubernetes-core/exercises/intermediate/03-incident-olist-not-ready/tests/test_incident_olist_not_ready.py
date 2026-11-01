import json
import time
from pathlib import Path

import pytest

from testkit import KUBE_IMAGES, Exercise, KubeLab

ex = Exercise(__file__)
INCIDENT = Path(__file__).parent / "fixtures" / "incident"
READYZ = ("import json, urllib.request; r = urllib.request.urlopen('http://api:8000/readyz', timeout=5); "
          "print(r.status, json.dumps(json.load(r)))")


def get_json(lab, *args):
    result = lab.kubectl("get", *args, "-o", "json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def worker_restarts(lab) -> int:
    pods = get_json(lab, "pods", "-l", "app.kubernetes.io/name=worker") or {"items": []}
    return sum(s.get("restartCount", 0) for p in pods["items"] for s in p["status"].get("containerStatuses") or [])


def endpoints(lab, ready_only: bool = True) -> list:
    slices = get_json(lab, "endpointslices", "-l", "kubernetes.io/service-name=api") or {"items": []}
    found = [e for s in slices["items"] for e in s.get("endpoints") or []]
    return [e for e in found if (e.get("conditions") or {}).get("ready")] if ready_only else found


def wait_for(check, timeout: float):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(3)
    return check()


@pytest.fixture(scope="module")
def fixed():
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab() as lab:
        state = {"applied": lab.apply_learner(ex.path("k8s"), check=False)}
        state["rollouts"] = {t: lab.kubectl("rollout", "status", t, "--timeout=120s", check=False).returncode
                             for t in ("statefulset/postgres", "deployment/redis", "deployment/api", "deployment/worker")}
        time.sleep(30)
        state["restarts"] = worker_restarts(lab)
        state["pvc"] = get_json(lab, "pvc", "data-postgres-0")
        state["events"] = lab.kubectl("get", "events", "--field-selector", "involvedObject.name=data-postgres-0",
                                      check=False).stdout
        state["endpoints"] = endpoints(lab)
        state["api_pods"] = (get_json(lab, "pods", "-l", "app.kubernetes.io/name=api") or {"items": []})["items"]
        state["readyz"] = lab.kubectl("exec", "deployment/worker", "--", "python", "-c", READYZ, check=False)
        yield state


@pytest.fixture(scope="module")
def incident():
    ex.require_cluster()
    ex.require_kind_images(KUBE_IMAGES["olist"], KUBE_IMAGES["postgres"], KUBE_IMAGES["redis"])
    with KubeLab() as lab:
        applied = lab.apply_learner(INCIDENT, check=False)
        yield lab, applied


def test_everything_rolls_out(fixed):
    assert fixed["applied"].returncode == 0, fixed["applied"].stderr
    assert fixed["rollouts"] == {t: 0 for t in fixed["rollouts"]}, f"Chưa rollout xong: {fixed['rollouts']}"


def test_postgres_volume_bound(fixed):
    pvc = fixed["pvc"]
    assert pvc and pvc["status"].get("phase") == "Bound", f"PVC data-postgres-0: {pvc and pvc['status']}\n{fixed['events']}"


def test_api_service_has_endpoints_and_answers(fixed):
    assert len(fixed["endpoints"]) >= 2, f"Service api có {len(fixed['endpoints'])} endpoint sẵn sàng"
    result = fixed["readyz"]
    assert result.returncode == 0 and result.stdout.startswith("200"), result.stdout + result.stderr[-400:]


def test_worker_stays_up(fixed):
    assert fixed["restarts"] == 0, f"Worker vẫn bị restart {fixed['restarts']} lần sau 30 giây"


def test_design_kept(fixed):
    labels = {p["metadata"]["labels"].get("app.kubernetes.io/name") for p in fixed["api_pods"]}
    assert labels == {"api"}, "Giữ nhãn app.kubernetes.io/name của pod (dashboard và NetworkPolicy dựa vào nó)"


def test_incident_reproduces_symptoms(incident):
    lab, applied = incident
    assert applied.returncode == 0, applied.stderr
    events = wait_for(lambda: "fast-ssd" in lab.kubectl("get", "events", "--field-selector",
                                                       "involvedObject.name=data-postgres-0", check=False).stdout, 90)
    assert events, "Bản lúc sự cố: PVC của postgres phải báo lỗi provisioning"
    assert get_json(lab, "pvc", "data-postgres-0")["status"].get("phase") == "Pending"
    assert wait_for(lambda: worker_restarts(lab) > 0, 120), "Bản lúc sự cố: worker phải bị restart"
    pods = (get_json(lab, "pods", "-l", "app.kubernetes.io/name=api") or {"items": []})["items"]
    assert pods and endpoints(lab, ready_only=False) == [], "Bản lúc sự cố: Service api không chọn được pod nào"
